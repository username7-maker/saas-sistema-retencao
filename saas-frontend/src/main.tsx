import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import * as Sentry from "@sentry/react";

import App from "./App";
import { AuthProvider } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { ThemedToaster } from "./components/ui2/ThemedToaster";
import "./index.css";
import "./styles/lovable-theme.css";
import { createAppQueryClient } from "./services/queryClient";

const sentryDsn = import.meta.env.VITE_SENTRY_DSN as string | undefined;
const releaseSha = (import.meta.env.VITE_RELEASE_SHA as string | undefined) || "dev";
document.documentElement.dataset.cordexRelease = releaseSha;
const releaseMeta = document.createElement("meta");
releaseMeta.name = "cordex-release";
releaseMeta.content = releaseSha;
document.head.appendChild(releaseMeta);
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: import.meta.env.MODE,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
    beforeSend(event) {
      delete event.user;
      if (event.request) {
        delete event.request.data;
        delete event.request.cookies;
        delete event.request.query_string;
        if (event.request.headers) {
          delete event.request.headers.Authorization;
          delete event.request.headers.authorization;
          delete event.request.headers.Cookie;
          delete event.request.headers.cookie;
        }
      }
      return event;
    },
  });
}

const queryClient = createAppQueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <AuthProvider>
            <App />
            <ThemedToaster />
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
);
