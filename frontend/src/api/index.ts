export const APP_ENV = import.meta.env.VITE_APP_ENV || "production";

export const API_BASE =
  APP_ENV === "local"
    ? "http://localhost:8000/api"
    : "/api";