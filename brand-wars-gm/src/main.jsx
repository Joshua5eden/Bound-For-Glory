import React from "react";
import ReactDOM from "react-dom/client";
import { initStorage } from "./storage.js";
import App from "./App.jsx";
import "./index.css";

initStorage();

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
