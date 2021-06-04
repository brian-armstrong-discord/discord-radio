import discord
from discord.ext import commands as discord_commands
import gnuradio
import gnuradio.analog
import gnuradio.audio
import gnuradio.filter
import gnuradio.gr
import numpy
import osmosdr


def make_source(sample_rate):
    source = osmosdr.source(args='rtl=0')
    source.set_freq_corr(0, 0)
    source.set_dc_offset_mode(0, 0)
    source.set_iq_balance_mode(0, 0)
    source.set_gain_mode(False, 0)
    source.set_if_gain(20, 0)
    source.set_bb_gain(20, 0)
    source.set_antenna("", 0)
    source.set_bandwidth(0, 0)
    source.set_gain(29.7)
    source.set_sample_rate(sample_rate)
    source.set_center_freq(88500000)
    return source


def make_resampler(num, denom):
    return gnuradio.filter.rational_resampler_ccc(
        interpolation=num,
        decimation=denom,
        taps=None,
        fractional_bw=None,
    )


def make_resampler_r(num, denom):
    return gnuradio.filter.rational_resampler_fff(
        interpolation=num,
        decimation=denom,
        taps=None,
        fractional_bw=None,
    )


def make_filter(decim, gain, sample_rate, cutoff_freq, transition_width):
    taps = gnuradio.filter.firdes.low_pass(
        gain,
        sample_rate,
        cutoff_freq,
        transition_width,
        firdes.WIN_HAMMING,
        6.76,
    )
    filt = gnuradio.filter.fir_filter_ccf(decim, taps)
    return filt


def make_wfm(input_rate, decim):
    return gnuradio.analog.wfm_rcv(
        quad_rate=input_rate,
        audio_decimation=decim,
    )


def make_audio(sample_rate):
    return gnuradio.audio.sink(sample_rate, "hw:0,0", True)


class CaptureBlock(gnuradio.gr.sync_block, discord.AudioSource):
    def __init__(self):
        gnuradio.gr.sync_block.__init__(
            self,
            name='Capture Block',
            in_sig=[numpy.float32],
            out_sig=[],
        )

        self.buffer = []
        self.buffer_len = 0
        self.playback_started = False
        self.min_buffer = int(48000 * 2 * 2 * 0.06)
        self.playback_length = int(48000 * 2 * 2 * 0.02)

        self.dtype = numpy.dtype('int16')
        self.dtype_i = numpy.iinfo(self.dtype)
        self.dtype_abs_max = 2 ** (self.dtype_i.bits - 1)

    def work(self, input_items, output_items):
        buf = self._convert(input_items[0])
        self.buffer_len += len(buf)
        self.buffer.append(buf)

        self.playback_started = self.buffer_len > self.min_buffer
        return len(input_items[0])

    def _convert(self, f):
        f = numpy.asarray(f)
        f = f * self.dtype_abs_max
        f = f.clip(self.dtype_i.min, self.dtype_i.max)
        f = f.astype(self.dtype)
        f = f.repeat(2)
        f = f.tobytes()
        return f

    def read(self):
        if not self.playback_started:
            return bytes(self.playback_length)

        buf = bytearray(self.playback_length)
        i = 0
        while i < self.playback_length:
            next_buf = self.buffer.pop(0)
            next_buf_len = len(next_buf)
            self.buffer_len -= next_buf_len
            if i + next_buf_len > self.playback_length:
                putback_len = next_buf_len - (self.playback_length - i)
                putback = next_buf[-putback_len:]
                self.buffer.insert(0, putback)
                self.buffer_len += putback_len
                next_buf = next_buf[:-putback_len]
                next_buf_len = len(next_buf)

            buf[i:i + next_buf_len] = next_buf
            i += next_buf_len

        return buf


class RadioBlock(gnuradio.gr.top_block):
    def __init__(self):
        gnuradio.gr.top_block.__init__(self, "Discord Radio")
        self.source_sample_rate = 2400000
        self.audio_sample_rate = 48000
        self.wfm_sample_rate = 200000
        self.wfm_output_rate = 200000 // 4

        self.source = make_source(self.source_sample_rate)
        self.resamp1 = make_resampler(1, self.source_sample_rate // self.wfm_sample_rate)
        self.wfm = make_wfm(self.wfm_sample_rate, 4)
        self.resamp2 = make_resampler_r(48, 50)
        self.capture_block = CaptureBlock()
        # self.audio = make_audio(self.audio_sample_rate)

        self.connect((self.source, 0), (self.resamp1, 0))
        self.connect((self.resamp1, 0), (self.wfm, 0))
        self.connect((self.wfm, 0), (self.resamp2, 0))
        # self.connect((self.resamp2, 0), (self.audio, 0))
        self.connect((self.resamp2, 0), (self.capture_block, 0))



bot = discord_commands.Bot(command_prefix=discord_commands.when_mentioned_or('!'),
                           description='Radio bot')


@bot.event
async def on_ready():
    print('Logged on')


class BotCommands(discord_commands.Cog):
    def __init__(self, bot, radio):
        self.bot = bot
        self.radio = radio

    @discord_commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()

    @discord_commands.command()
    async def fm(self, ctx, *, freq):
        freq_mhz = float(freq)
        freq = float(freq_mhz) * 1000000
        self.radio.source.set_center_freq(freq)

        if not ctx.voice_client.is_playing():
            source = discord.PCMVolumeTransformer(self.radio.capture_block)
            ctx.voice_client.play(source)
            self.radio.start()

        await ctx.send(f'Tuning {freq_mhz}MHz FM')

    @discord_commands.command()
    async def stop(self, ctx):
        self.radio.stop()
        await ctx.voice_client.disconnect() 

    @fm.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send('You must be in a voice channel to use that')
                raise discord_commands.CommandError('User not connected to voice channel')


if __name__ == '__main__':
    import sys
    token = sys.argv[1]
    top_block = RadioBlock()
    bot.add_cog(BotCommands(bot, top_block))
    bot.run(token)