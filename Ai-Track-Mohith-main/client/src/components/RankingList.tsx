import {
  Box,
  Chip,
  LinearProgress,
  Tooltip,
  Typography,
} from "@mui/material";
import type {
  CandidateScorecard,
  RankingEntry,
} from "../lib/hirelogic";

interface Props {
  ranking: RankingEntry[];
  scorecard: Record<string, CandidateScorecard>;
  expanded: string | null;
  onToggle: (candidateId: string) => void;
}

export function RankingList({
  ranking,
  scorecard,
  expanded,
  onToggle,
}: Props) {
  const rankColors = ["#FFD700", "#C0C0C0", "#CD7F32"];

  return (
    <>
      {ranking.map((entry, index) => {
        const candidate = scorecard[entry.anon_id];
        const isOpen = expanded === entry.anon_id;
        return (
          <Box key={entry.anon_id} sx={{ mb: 1.5 }}>
            <Box
              onClick={() => onToggle(isOpen ? "" : entry.anon_id)}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1.5,
                cursor: "pointer",
                p: 1,
                borderRadius: 1,
                "&:hover": { bgcolor: "action.hover" },
              }}
            >
              <Typography sx={{ fontSize: 18, color: rankColors[index] ?? "text.secondary" }}>
                #{entry.rank}
              </Typography>
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="body2" fontWeight={600}>
                  {entry.anon_id}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={entry.overall_score * 10}
                  sx={{
                    mt: 0.5,
                    height: 6,
                    borderRadius: 3,
                    bgcolor: "action.hover",
                    "& .MuiLinearProgress-bar": {
                      bgcolor:
                        index === 0
                          ? "success.main"
                          : index === 1
                            ? "primary.main"
                            : "text.secondary",
                    },
                  }}
                />
              </Box>
              <Typography variant="body2" fontWeight={700} color="text.primary">
                {entry.overall_score.toFixed(1)}/10
              </Typography>
              {candidate?.low_confidence && (
                <Chip label="Low confidence" size="small" color="warning" variant="outlined" />
              )}
            </Box>

            {isOpen && candidate && (
              <Box sx={{ pl: 2, pr: 1, pb: 1, display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                {Object.entries(candidate.competency_scores).map(([competency, data]) => (
                  <Tooltip key={competency} title={data.explanation} arrow>
                    <Chip
                      label={`${competency}: ${data.score.toFixed(1)}`}
                      size="small"
                      color={
                        data.score >= 7 ? "success" : data.score >= 5 ? "primary" : "default"
                      }
                      variant="outlined"
                      sx={{ cursor: "help" }}
                    />
                  </Tooltip>
                ))}
              </Box>
            )}
          </Box>
        );
      })}
    </>
  );
}
