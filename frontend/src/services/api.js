import React from "react";

const API_URL = process.env.REACT_APP_API_URL ?? "http://localhost:5050";

export async function getData() {
  try {
    const response = await fetch(`${API_URL}/data`);
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    const data = await response.json();
    console.log("API returned:", data);
    return data;
  } catch (err) {
    console.error("Failed to fetch data from backend:", err);
    throw err;
  }
}
