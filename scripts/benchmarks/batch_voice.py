import time
import asyncio
from pathlib import Path
from common import BASE_DIR, benchmark_call, save_batch_results
from services.tts import generate_speech, generate_speech_with_ttfa, stream_speech_chunks
from services.brain.engine import respond


def run_batch_voice():
    print("\n🚀 [BATCH B] Running Voice Pipeline (STT & TTS) Benchmarks...")
    temp_dir = BASE_DIR / "backend" / "temp_audio"
    temp_dir.mkdir(parents=True, exist_ok=True)
    results = []

    # 1. Real Edge-TTS TTFA (Time To First Audio)
    def test_real_edge_tts_ttfa():
        _, ttfa_ms, _ = asyncio.run(
            generate_speech_with_ttfa("Good evening Prem. All systems operational.", temp_dir)
        )
        return ttfa_ms

    results.append(benchmark_call(
        name="TTS: Edge-TTS Time To First Audio (TTFA)",
        category="TTS",
        mode="LOCAL_REAL",
        fn=test_real_edge_tts_ttfa,
        iterations=8,
        warmup=1,
        timeout_sec=5.0,
    ))

    # 2. Real Edge-TTS Total Synthesis Duration
    def test_real_edge_tts_total():
        return asyncio.run(generate_speech("Good evening Prem. All systems operational.", temp_dir))

    results.append(benchmark_call(
        name="TTS: Edge-TTS Audio Synthesis Total (~45 chars)",
        category="TTS",
        mode="LOCAL_REAL",
        fn=test_real_edge_tts_total,
        iterations=8,
        warmup=1,
        timeout_sec=5.0,
    ))

    # 3. Early Sentence Chunk Synthesis
    async def _test_chunk_first():
        async for chunk in stream_speech_chunks(
            "Display locked, Prem. All background sessions remain secured.", temp_dir
        ):
            return chunk

    def test_first_sentence_chunk():
        return asyncio.run(_test_chunk_first())

    results.append(benchmark_call(
        name="TTS: First Sentence Chunk Synthesis (Early Burst)",
        category="TTS",
        mode="LOCAL_REAL",
        fn=test_first_sentence_chunk,
        iterations=8,
        warmup=1,
        timeout_sec=5.0,
    ))

    # 4. Mock TTS Synthesis
    def test_mock_tts():
        time.sleep(0.005)
        return {"audio_url": "/temp_audio/mock_uuid.mp3", "duration": 1.5}

    results.append(benchmark_call(
        name="TTS: In-Memory Audio Mock Generator",
        category="TTS",
        mode="MOCK",
        fn=test_mock_tts,
        iterations=40,
    ))

    # 5. Mock STT Transcription
    def test_mock_stt():
        time.sleep(0.020)  # 20ms simulated local Whisper STT
        return {"transcript": "open trading"}

    results.append(benchmark_call(
        name="STT: Simulated Local Whisper Engine",
        category="STT",
        mode="MOCK",
        fn=test_mock_stt,
        iterations=40,
    ))

    # 6. End-to-End Fast-Path Voice Round Trip (STT -> Fast Brain -> Mock TTS)
    def test_e2e_voice_round_trip():
        stt = test_mock_stt()["transcript"]
        b_res = respond(stt, is_boss=True, silence_tts=True)
        return b_res

    results.append(benchmark_call(
        name="Voice: E2E Fast-Path Round Trip (STT -> Brain -> Response)",
        category="Voice_E2E",
        mode="LOCAL_REAL",
        fn=test_e2e_voice_round_trip,
        iterations=30,
    ))

    save_batch_results("batch_voice", results)


if __name__ == "__main__":
    run_batch_voice()
