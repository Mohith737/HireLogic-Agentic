import { Box, Paper } from "@mui/material";
import { LoginContainer } from "../containers/LoginContainer";

export function LoginPage() {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        px: 2,
        background: "linear-gradient(135deg, #0f1117 0%, #1a237e 100%)",
      }}
    >
      <Paper
        elevation={8}
        sx={{
          width: 420,
          p: 5,
          borderRadius: "16px",
          backgroundColor: "#ffffff",
        }}
      >
        <LoginContainer />
      </Paper>
    </Box>
  );
}
