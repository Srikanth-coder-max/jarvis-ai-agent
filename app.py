import streamlit as st

from core.brain import Brain
from core.llm_client import LLMClient
from config import LLM_PROVIDER


@st.cache_resource
def get_brain() -> Brain:
    return Brain(LLMClient())


@st.cache_resource
def get_stt():
    try:
        from voice.stt import STT
    except Exception:
        return None

    return STT()


@st.cache_resource
def get_tts():
    try:
        from voice.tts import TTS
    except Exception:
        return None

    return TTS()


def get_browser_audio_transcript(audio_file):
    stt = get_stt()
    if stt is None:
        return "STT Error: Voice input is unavailable in this deployment."

    return stt.transcribe_uploaded_audio(audio_file)


def reset_chat() -> None:
    brain = get_brain()
    brain.reset()
    st.session_state.messages = []


def ask_jarvis(prompt: str, auto_speak: bool) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            brain = get_brain()
            response = brain.chat(prompt)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

    if auto_speak:
        with st.spinner("Speaking..."):
            tts = get_tts()
            if tts is None:
                st.warning("Voice output is unavailable in this deployment.")
                return
            tts.speak(response)


def main() -> None:
    st.set_page_config(page_title="Jarvis", page_icon="J", layout="centered")

    st.title("Jarvis Assistant")
    st.caption(f"Provider: {LLM_PROVIDER}")

    with st.sidebar:
        st.subheader("Controls")
        if st.button("Reset memory", use_container_width=True):
            reset_chat()
            st.success("Memory cleared.")

        st.subheader("Voice mode")
        auto_speak = st.checkbox("Auto-speak replies", value=False)
        speak_last = st.button("Speak last reply", use_container_width=True)

        st.caption("Use the audio recorder below to speak from your browser.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if speak_last:
        last_reply = ""
        for msg in reversed(st.session_state.messages):
            if msg.get("role") == "assistant":
                last_reply = msg.get("content", "")
                break

        if last_reply:
            with st.spinner("Speaking last reply..."):
                tts = get_tts()
                if tts is None:
                    st.warning("Voice output is unavailable in this deployment.")
                else:
                    tts.speak(last_reply)
        else:
            st.info("No assistant reply to speak yet.")

    voice_prompt = ""
    browser_audio = st.audio_input("Record audio in your browser", help="Click the mic, speak, then stop recording.")
    if browser_audio is not None:
        if st.button("Transcribe recording", use_container_width=True):
            with st.spinner("Transcribing browser audio..."):
                transcript = get_browser_audio_transcript(browser_audio)

            if not transcript:
                st.warning("No voice input captured.")
            elif "STT Error" in transcript:
                st.error(transcript)
            else:
                voice_prompt = transcript.strip()
                st.info(f"You said: {voice_prompt}")

    prompt = st.chat_input("Ask Jarvis anything...")
    final_prompt = voice_prompt if voice_prompt else (prompt or "")
    if not final_prompt:
        return

    ask_jarvis(final_prompt, auto_speak)


if __name__ == "__main__":
    main()
