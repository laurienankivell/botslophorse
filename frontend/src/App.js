import React, { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [comments, setComments] = useState([]);
  const [commentIndex, setCommentIndex] = useState(0);
  const [isStopped, setIsStopped] = useState(true);
  const [horseImg, setHorseImg] = useState("horse_silent.png");

  const synth = window.speechSynthesis;

  useEffect(() => {
    fetch("live_horse_data.json")
      .then((response) => response.json())
      .then((data) => {
        setComments(data.map((item) => item.text));
        console.log("Horse is loaded with " + data.length + " rants.");
      })
      .catch((err) => {
        console.error("Data failed to load.", err);
      });
  }, []);

  const speakComment = (text) => {
    synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.8;
    utterance.pitch = 0.7;

    utterance.onstart = () => {
      setHorseImg("horse_talking.gif");
    };

    utterance.onend = () => {
      setHorseImg("horse_silent.png");
      if (!isStopped) {
        setTimeout(playNext, 2000);
      }
    };

    synth.speak(utterance);
  };

  const playNext = () => {
    if (comments.length === 0) return;

    let nextIndex = commentIndex;
    if (nextIndex >= comments.length) {
      nextIndex = 0;
    }

    const nextComment = comments[nextIndex];
    setCommentIndex(nextIndex + 1);
    speakComment(nextComment);
  };

  const startRanting = () => {
    if (isStopped) {
      setIsStopped(false);
      playNext();
    }
  };

  const stopAndSkip = () => {
    setIsStopped(false);
    synth.cancel();
  };

  const stopAndSilence = () => {
    setIsStopped(true);
    synth.cancel();
    setHorseImg("horse_silent.png");
  };

  return (
    <div className="App">
      <h1 style={{ marginTop: "10px" }}>🐎 THE BOTSLOP HORSE 🐎</h1>
      <img id="horse-img" src={horseImg} alt="Horse" />
      <div className="controls">
        <button onClick={startRanting}>📢 Start Ranting</button>
        <button onClick={stopAndSkip}>➡️ Next Rant</button>
        <button onClick={stopAndSilence}>🛑 Stop Ranting</button>
      </div>
    </div>
  );
}

export default App;
