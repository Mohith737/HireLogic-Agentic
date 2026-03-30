import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { logout, useAuth } from "../lib/auth";

export function Navbar() {
  const { data: user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const handleLogout = () => {
    logout();
    queryClient.clear();
    navigate("/login");
  };

  return (
    <AppBar
      position="sticky"
      sx={{ bgcolor: "#111827", borderBottom: 1, borderColor: "divider" }}
      elevation={0}
    >
      <Toolbar>
        <Box
          component={Link}
          to="/hirelogic"
          sx={{ display: "flex", alignItems: "center", gap: 1, textDecoration: "none", flexGrow: 1 }}
        >
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: 2,
              background: "linear-gradient(135deg, #0f766e, #2563eb)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 12,
              color: "white",
            }}
          >
            HL
          </Box>
          <Typography variant="subtitle1" fontWeight={600} color="#FFFFFF">
            HireLogic
          </Typography>
        </Box>

        <Box sx={{ display: "flex", gap: 1, alignItems: "center" }}>
          <Button component={Link} to="/hirelogic" color="inherit" size="small" sx={{ color: "#FFFFFF" }}>
            HireLogic
          </Button>
          {user ? (
            <>
              <Typography variant="body2" sx={{ mx: 1, color: "rgba(255,255,255,0.72)" }}>
                {user.username}
              </Typography>
              <Button onClick={handleLogout} color="inherit" size="small" sx={{ color: "#FFFFFF" }}>
                Logout
              </Button>
            </>
          ) : (
            <Button component={Link} to="/login" variant="contained" size="small">
              Login
            </Button>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
}
