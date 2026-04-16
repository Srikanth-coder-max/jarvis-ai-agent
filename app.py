import streamlit as st

from core.brain import Brain
from core.llm_client import LLMClient
from config import LLM_PROVIDER
from voice.stt import STT
from voice.tts import TTS


@st.cache_resource
def get_brain() -> Brain:
    return Brain(LLMClient())


@st.cache_resource
def get_stt() -> STT:
    return STT()


@st.cache_resource
def get_tts() -> TTS:
    return TTS()


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
        voice_duration = st.slider("Listen duration (seconds)", min_value=3, max_value=20, value=7, step=1)
        auto_speak = st.checkbox("Auto-speak replies", value=False)
        start_voice = st.button("Start listening", use_container_width=True)
        speak_last = st.button("Speak last reply", use_container_width=True)

        # st.subheader("Try these")
        # st.markdown("- What is the latest AI news this week?")
        # st.markdown("- Check my system usage")
        # st.markdown("- What is the weather in Chennai?")

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
                tts.speak(last_reply)
        else:
            st.info("No assistant reply to speak yet.")

    voice_prompt = ""
    if start_voice:
        with st.spinner("Listening..."):
            stt = get_stt()
            transcript = stt.listen(voice_duration)

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
