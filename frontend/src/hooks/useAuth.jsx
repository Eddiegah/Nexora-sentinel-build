import React, { createContext, useContext, useState } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("nexora_token"));

  function saveToken(t) {
    localStorage.setItem("nexora_token", t);
    setToken(t);
  }

  function clearToken() {
    localStorage.removeItem("nexora_token");
    setToken(null);
  }

  return (
    <AuthContext.Provider value={{ token, saveToken, clearToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
