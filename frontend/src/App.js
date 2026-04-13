import React, { useState, useEffect, useRef } from "react";
import { getData } from "./services/api";
import "./App.css";

function App() {
  // UI State (things we want to trigger visual re-renders)
  const [comments, setComments] = useState([]);
  const [horseImg, setHorseImg] = useState("horse_silent.png");

  // Logic Refs (live variables for the speech synthesizer)
  const commentsRef = useRef([]);
  const commentIndexRef = useRef(0);
  const isStoppedRef = useRef(true);

  const synth = window.speechSynthesis;

  useEffect(() => {
    async function loadData() {
      try {
        const data = await getData();
        const textArray = data.map((item) => item.text);
        
        // Update both the UI state and our logic ref
        setComments(textArray);
        commentsRef.current = textArray; 
        
        console.log("Backend loaded with " + textArray.length + " comments.");
      } catch (err) {
        console.error("Data failed to load.", err);
      }
    }
    loadData();
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
      
      // Look at the live REF, not the state!
      if (!isStoppedRef.current) {
        setTimeout(playNext, 2000);
      }
    };

    synth.speak(utterance);
  };

  const playNext = () => {
    const currentList = commentsRef.current;
    if (currentList.length === 0) return;

    let nextIndex = commentIndexRef.current;
    if (nextIndex >= currentList.length) {
      nextIndex = 0; // Loop back to the start
    }

    const nextComment = currentList[nextIndex];
    
    // Increment the ref for the next round
    commentIndexRef.current = nextIndex + 1; 
    
    speakComment(nextComment);
  };

  const startRanting = () => {
    if (isStoppedRef.current) {
      isStoppedRef.current = false;
      playNext();
    }
  };

  const stopAndSkip = () => {
    // Simply cancelling the current speech will trigger the 'onend' 
    // event, which automatically fires the next rant!
    synth.cancel();
  };

  const stopAndSilence = () => {
    isStoppedRef.current = true;
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