import { useState } from "react";
import PersonIcon from "@mui/icons-material/Person";
import LockIcon from "@mui/icons-material/Lock";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import {
  Alert,
  Avatar,
  Box,
  Button,
  CircularProgress,
  IconButton,
  InputAdornment,
  TextField,
  Typography,
} from "@mui/material";
import { useQueryClient } from "@tanstack/react-query";
import { Navigate, useNavigate } from "react-router-dom";
import { loginWithPassword, useAuth } from "../lib/auth";

const FIELD_SX = {
  mb: 2,
  "& .MuiOutlinedInput-root": {
    backgroundColor: "#f8f9fa",
  },
  "& .MuiInputBase-input": {
    color: "#0f1117",
    fontSize: "1rem",
  },
  "& .MuiInputLabel-root": {
    color: "#555",
  },
  "& .MuiInputLabel-root.Mui-focused": {
    color: "#1565c0",
  },
  "& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-notchedOutline": {
    borderColor: "#1565c0",
  },
};

export function LoginContainer() {
  const { data: user, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  if (!authLoading && user) {
    return <Navigate to="/hirelogic" replace />;
  }

  const handleLogin = async () => {
    if (!username || !password || isLoading) {
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      await loginWithPassword(username, password);
      queryClient.invalidateQueries({ queryKey: ["auth-user"] });
      navigate("/hirelogic");
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(message ?? "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Box sx={{ textAlign: "center", mb: 4 }}>
        <Avatar
          sx={{
            bgcolor: "#1565c0",
            width: 56,
            height: 56,
            margin: "0 auto 16px",
            fontSize: "1.4rem",
            fontWeight: 700,
          }}
        >
          HL
        </Avatar>
        <Typography variant="h5" sx={{ fontWeight: 700, color: "#0f1117", mb: 0.5 }}>
          HireLogic
        </Typography>
        <Typography variant="body2" sx={{ color: "#555", fontSize: "0.875rem" }}>
          AI-powered candidate screening platform
        </Typography>
      </Box>

      <TextField
        fullWidth
        label="Username"
        value={username}
        onChange={(event) => setUsername(event.target.value)}
        onKeyDown={(event) => event.key === "Enter" && void handleLogin()}
        sx={FIELD_SX}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <PersonIcon sx={{ color: "#555" }} />
            </InputAdornment>
          ),
        }}
      />

      <TextField
        fullWidth
        label="Password"
        type={showPassword ? "text" : "password"}
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        onKeyDown={(event) => event.key === "Enter" && void handleLogin()}
        sx={FIELD_SX}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <LockIcon sx={{ color: "#555" }} />
            </InputAdornment>
          ),
          endAdornment: (
            <InputAdornment position="end">
              <IconButton onClick={() => setShowPassword((prev) => !prev)} edge="end" sx={{ color: "#555" }}>
                {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
              </IconButton>
            </InputAdornment>
          ),
        }}
      />

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <Button
        fullWidth
        variant="contained"
        size="large"
        disabled={isLoading || !username || !password}
        onClick={() => void handleLogin()}
        sx={{
          backgroundColor: "#1565c0",
          color: "#ffffff",
          fontWeight: 700,
          fontSize: "1rem",
          py: 1.5,
          borderRadius: 2,
          textTransform: "none",
          "&:hover": { backgroundColor: "#0d47a1" },
          "&:disabled": {
            backgroundColor: "#90caf9",
            color: "#ffffff",
          },
        }}
      >
        {isLoading ? <CircularProgress size={24} sx={{ color: "#fff" }} /> : "Sign In"}
      </Button>

      <Typography
        variant="caption"
        sx={{ color: "#888", display: "block", textAlign: "center", mt: 2 }}
      >
        Demo: recruiter_alice / pass1234
      </Typography>
    </>
  );
}
