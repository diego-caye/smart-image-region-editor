import React from "react";
import ReactDOM from "react-dom/client";
import { EditSessionProvider } from "./infrastructure/state/EditSessionContext";
import { EditorPage } from "./presentation/pages/EditorPage";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <EditSessionProvider>
      <EditorPage />
    </EditSessionProvider>
  </React.StrictMode>,
);
