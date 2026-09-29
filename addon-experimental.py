import ctypes
import xbmc
import xbmcvfs


# --- C-STRUCTURES ---
class AVCodecContext(ctypes.Structure):
    pass


class AVFormatContext(ctypes.Structure):
    pass


class AVCodecParameters(ctypes.Structure):
    _fields_ = [("codec_type", ctypes.c_int), ("codec_id", ctypes.c_int)]


class AVStream(ctypes.Structure):
    _fields_ = [
        ("index", ctypes.c_int),
        ("id", ctypes.c_int),
        ("codecptr", ctypes.c_void_p),
        ("time_base", ctypes.c_int * 2),
        ("start_time", ctypes.c_int64),
        ("duration", ctypes.c_int64),
        ("nb_frames", ctypes.c_int64),
        ("disposition", ctypes.c_int),
        ("discard", ctypes.c_int),
        ("sample_aspect_ratio", ctypes.c_int * 2),
        ("metadata", ctypes.c_void_p),
        ("avg_frame_rate", ctypes.c_int * 2),
        ("attached_pic", ctypes.c_void_p),
        ("display_aspect_ratio", ctypes.c_int * 2),
        ("priv_data", ctypes.c_void_p),
        ("codecpar", ctypes.POINTER(AVCodecParameters)),
    ]


class AVFormatContext(ctypes.Structure):
    _fields_ = [
        ("av_class", ctypes.c_void_p),
        ("iformat", ctypes.c_void_p),
        ("priv_data", ctypes.c_void_p),
        ("pb", ctypes.c_void_p),
        ("ctx_flags", ctypes.c_int),
        ("nb_streams", ctypes.c_uint),
        ("streams", ctypes.POINTER(ctypes.POINTER(AVStream))),
    ]


class AVPacket(ctypes.Structure):
    _fields_ = [
        ("buf", ctypes.c_void_p),
        ("pts", ctypes.c_int64),
        ("dts", ctypes.c_int64),
        ("data", ctypes.POINTER(ctypes.c_ubyte)),
        ("size", ctypes.c_int),
        ("stream_index", ctypes.c_int),
    ]


class AVFrame(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_ubyte) * 8),
        ("linesize", ctypes.c_int * 8),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
    ]


# --- LOAD LIBRARIES & MAPPINGS ---
lib = ctypes.CDLL("libkodi.so", mode=ctypes.RTLD_GLOBAL)

# Core mappings
lib.avformat_open_input.argtypes = [
    ctypes.c_void_p,
    ctypes.c_char_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
lib.avformat_find_stream_info.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
lib.av_read_frame.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
lib.av_seek_frame.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int64,
    ctypes.c_int,
]
lib.avformat_close_input.argtypes = [ctypes.c_void_p]

# Codec mappings
lib.avcodec_find_decoder.restype = ctypes.c_void_p
lib.avcodec_alloc_context3.restype = ctypes.POINTER(AVCodecContext)
lib.avcodec_send_packet.argtypes = [
    ctypes.POINTER(AVCodecContext),
    ctypes.POINTER(AVPacket),
]
lib.avcodec_receive_frame.argtypes = [
    ctypes.POINTER(AVCodecContext),
    ctypes.POINTER(AVFrame),
]
lib.avcodec_free_context.argtypes = [ctypes.POINTER(ctypes.POINTER(AVCodecContext))]

# Alloc/Free mappings
lib.av_frame_alloc.restype = ctypes.POINTER(AVFrame)
lib.av_frame_free.argtypes = [ctypes.POINTER(ctypes.POINTER(AVFrame))]
lib.av_packet_alloc.restype = ctypes.POINTER(AVPacket)
lib.av_packet_free.argtypes = [ctypes.POINTER(ctypes.POINTER(AVPacket))]
lib.av_packet_unref.argtypes = [ctypes.POINTER(AVPacket)]

# Add these to your FUNCTION MAPPINGS
lib.avcodec_parameters_to_context.argtypes = [
    ctypes.POINTER(AVCodecContext),
    ctypes.c_void_p,
]
lib.avcodec_parameters_to_context.restype = ctypes.c_int


lib.av_find_best_stream.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_int,
]
lib.av_find_best_stream.restype = ctypes.c_int

lib.avcodec_find_decoder.argtypes = [ctypes.c_int]
lib.avcodec_find_decoder.restype = ctypes.c_void_p

lib.av_dict_set.argtypes = [
    ctypes.POINTER(ctypes.c_void_p),
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.c_int,
]
lib.av_dict_free.argtypes = [ctypes.POINTER(ctypes.c_void_p)]

lib.av_packet_free.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
lib.av_frame_free.argtypes = [ctypes.POINTER(ctypes.c_void_p)]


AVMEDIA_TYPE_VIDEO = 0


def scan_y_plane(luma_ptr, stride, height, width):
    threshold = 20  # Standard Y black level
    mid_x = width // 2
    for y in range(height // 2):
        # Accessing the Y plane data via pointer arithmetic
        pixel_val = luma_ptr[y * stride + mid_x]
        if pixel_val > threshold:
            return y
    return 0


def detect_bars_live(file_url, timestamp):
    xbmc.log("DEBUG_SCAN: [Step 1] Opening input...", xbmc.LOGINFO)
    fmt_ctx = ctypes.c_void_p(0)
    codec_ctx = ctypes.c_void_p(0)
    options = ctypes.c_void_p(0)

    # Limit the probe to 2MB to prevent the OOM crash you saw
    lib.av_dict_set(ctypes.byref(options), b"probesize", b"2000000", 0)
    lib.av_dict_set(ctypes.byref(options), b"analyzeduration", b"2000000", 0)

    # 1. Open Input

    res = lib.avformat_open_input(
        ctypes.byref(fmt_ctx), file_url.encode("utf-8"), None, ctypes.byref(options)
    )

    # Clean up the dictionary memory immediately
    lib.av_dict_free(ctypes.byref(options))

    if res != 0:
        return None

    try:
        lib.avformat_find_stream_info(fmt_ctx, None)

        # 2. Let FFmpeg find the best stream and the decoder for us automatically
        # This function returns the stream index and can optionally return the decoder
        target_decoder = ctypes.c_void_p(0)
        v_idx = lib.av_find_best_stream(
            fmt_ctx, 0, -1, -1, ctypes.byref(target_decoder), 0
        )

        if v_idx < 0 or not target_decoder:
            xbmc.log(
                "DEBUG_SCAN: [FAIL] Could not find video stream or decoder",
                xbmc.LOGINFO,
            )
            return None

        # 3. Setup Context
        codec_ctx = lib.avcodec_alloc_context3(target_decoder)

        # Safer way to get the streams pointer
        ctx_ptr = ctypes.cast(fmt_ctx, ctypes.POINTER(ctypes.c_void_p * 20))
        streams_ptr = ctx_ptr.contents[6]  # nb_streams is index 5, streams is 6
        stream_ptr = ctypes.cast(
            streams_ptr, ctypes.POINTER(ctypes.c_void_p * 100)
        ).contents[v_idx]

        # Find codecpar offset (it's the only POINTER in AVStream we need)
        # We try a safer way: copy from the stream index FFmpeg gave us
        if (
            lib.avcodec_parameters_to_context(
                codec_ctx, ctypes.cast(stream_ptr, ctypes.c_void_p)
            )
            < 0
        ):
            # If direct cast fails, we use the most common offset for codecpar (130-140 bytes in)
            codecpar_ptr = ctypes.c_void_p(stream_ptr.value + 136)
            lib.avcodec_parameters_to_context(codec_ctx, codecpar_ptr)

        if lib.avcodec_open2(codec_ctx, target_decoder, None) == 0:
            xbmc.log(
                f"DEBUG_SCAN: [SUCCESS] Decoder opened for stream {v_idx}", xbmc.LOGINFO
            )
        else:
            return None

        # 5. Seek and Decode
        lib.av_seek_frame(fmt_ctx, -1, int(timestamp * 1000000), 1)
        frame = lib.av_frame_alloc()
        packet = lib.av_packet_alloc()

        for _ in range(50):
            if lib.av_read_frame(fmt_ctx, packet) < 0:
                break
            # Check stream index at offset 24 or 32
            p_idx = ctypes.cast(packet, ctypes.POINTER(ctypes.c_int * 10)).contents[8]
            if p_idx == v_idx:
                if lib.avcodec_send_packet(codec_ctx, packet) == 0:
                    if lib.avcodec_receive_frame(codec_ctx, frame) == 0:
                        top = scan_y_plane(
                            frame.contents.data[0],
                            frame.contents.linesize[0],
                            frame.contents.height,
                            frame.contents.width,
                        )
                        xbmc.log(f"DEBUG_SCAN: Detected Bar: {top}px", xbmc.LOGINFO)
                        break
            lib.av_packet_unref(packet)

    finally:
        # Proper memory cleanup for Android
        if packet:
            lib.av_packet_free(ctypes.byref(packet))
        if frame:
            lib.av_frame_free(ctypes.byref(frame))
        if codec_ctx:
            lib.avcodec_free_context(ctypes.byref(codec_ctx))
        if fmt_ctx:
            # THIS IS CRITICAL to prevent the OOM crash
            lib.avformat_close_input(ctypes.byref(fmt_ctx))


class BarScanner(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        # You MUST initialize the player here
        self.player = xbmc.Player()

    def run(self):
        while not self.abortRequested():
            if self.player.isPlayingVideo():
                raw_url = self.player.getPlayingFile()
                # Translate to a real URL if possible
                translated_url = xbmcvfs.translatePath(raw_url)

                if translated_url.startswith("dav://"):
                    translated_url = translated_url.replace("dav://", "http://", 1)
                elif translated_url.startswith("davs://"):
                    translated_url = translated_url.replace("davs://", "https://", 1)

                curr_time = self.player.getTime()

                # Run the C-linked detection with the translated URL
                detect_bars_live(translated_url, curr_time)
            if self.waitForAbort(15):
                break


if __name__ == "__main__":
    BarScanner().run()
