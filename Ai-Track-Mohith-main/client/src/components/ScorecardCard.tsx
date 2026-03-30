import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import type { CandidateScorecard, RankingEntry } from "../lib/hirelogic";

interface Props {
  ranking: RankingEntry[];
  scorecard: Record<string, CandidateScorecard>;
}

const RANK_LABELS = ["🥇", "🥈", "🥉"];

function cleanEvidence(raw: string): string {
  if (!raw) return "";
  const cleaned = raw
    .replace(/^[\s\-•]+/, "")
    .replace(/\s*-\s*/g, ". ")
    .replace(/\.\s*\./g, ".")
    .trim();
  const firstSentence = cleaned.split(/\.\s+/)[0];
  return firstSentence.length > 120
    ? `${firstSentence.substring(0, 117)}...`
    : firstSentence;
}

export function ScorecardCard({ ranking, scorecard }: Props) {
  if (!ranking || ranking.length === 0) {
    return null;
  }

  return (
    <Box
      sx={{
        mt: 1,
        backgroundColor: "#FFFFFF",
        border: "1px solid #E0E0E0",
        borderRadius: "8px",
        p: 2,
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: "#1565c0",
          fontSize: "0.75rem",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          display: "block",
          mb: 1,
        }}
      >
        🏆 Ranking Results
      </Typography>

      {ranking.map((entry, index) => {
        const candidate = scorecard[entry.anon_id];

        return (
          <Accordion
            key={entry.anon_id}
            defaultExpanded={index === 0}
            sx={{
              border: "1px solid #e0e0e0",
              borderRadius: "8px !important",
              mb: 1,
              "&:before": { display: "none" },
              boxShadow: "none",
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon sx={{ color: "#1565c0" }} />}
              sx={{
                minHeight: 56,
                "& .MuiAccordionSummary-content": {
                  alignItems: "center",
                  gap: 1.5,
                },
              }}
            >
              <Typography sx={{ fontSize: "1.4rem" }}>
                {RANK_LABELS[index] ?? `#${entry.rank}`}
              </Typography>
              <Typography
                variant="subtitle1"
                sx={{ fontWeight: 600, color: "#0f1117", flex: 1 }}
              >
                {entry.anon_id}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <LinearProgress
                  variant="determinate"
                  value={entry.overall_score * 10}
                  sx={{
                    width: 100,
                    height: 8,
                    borderRadius: 4,
                    backgroundColor: "#e0e0e0",
                    "& .MuiLinearProgress-bar": {
                      backgroundColor:
                        entry.overall_score >= 7
                          ? "#1565c0"
                          : entry.overall_score >= 5
                            ? "#f9a825"
                            : "#c62828",
                      borderRadius: 4,
                    },
                  }}
                />
                <Typography
                  variant="subtitle1"
                  sx={{ fontWeight: 700, color: "#0f1117", minWidth: 45 }}
                >
                  {entry.overall_score.toFixed(1)}/10
                </Typography>
              </Box>
              {candidate?.low_confidence && (
                <Chip
                  label="Low confidence"
                  size="small"
                  color="warning"
                  sx={{ fontSize: "0.65rem" }}
                />
              )}
            </AccordionSummary>

            <AccordionDetails sx={{ pt: 0, px: 2, pb: 2 }}>
              <Divider sx={{ mb: 1.5 }} />
              {candidate &&
                Object.entries(candidate.competency_scores).map(([name, comp]) => (
                  <Box key={name} sx={{ mb: 2 }}>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        mb: 0.75,
                      }}
                    >
                      <Typography
                        variant="body2"
                        sx={{ fontWeight: 600, color: "#1a1a1a" }}
                      >
                        {name}
                      </Typography>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        {comp.interview_feedback_used && (
                          <Chip
                            label="Interview ✓"
                            size="small"
                            sx={{
                              fontSize: "0.6rem",
                              height: 18,
                              backgroundColor: "#e3f2fd",
                              color: "#1565c0",
                            }}
                          />
                        )}
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 700,
                            color:
                              comp.score >= 7
                                ? "#1b5e20"
                                : comp.score >= 5
                                  ? "#e65100"
                                  : "#b71c1c",
                          }}
                        >
                          {comp.score.toFixed(1)}/10
                        </Typography>
                        <Typography variant="caption" sx={{ color: "#999" }}>
                          × {Number(comp.weight).toFixed(2)}
                        </Typography>
                      </Box>
                    </Box>

                    <LinearProgress
                      variant="determinate"
                      value={comp.score * 10}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        backgroundColor: "#f5f5f5",
                        mb: 0.75,
                        "& .MuiLinearProgress-bar": {
                          backgroundColor:
                            comp.score >= 7
                              ? "#2e7d32"
                              : comp.score >= 5
                                ? "#f57c00"
                                : "#c62828",
                          borderRadius: 3,
                        },
                      }}
                    />

                    {comp.evidence && (
                      <Typography
                        variant="caption"
                        sx={{
                          color: "#555",
                          fontStyle: "italic",
                          display: "block",
                          backgroundColor: "#f8f9fa",
                          px: 1.5,
                          py: 0.75,
                          borderRadius: 1,
                          borderLeft: "3px solid #1565c0",
                          mb: 0.5,
                          lineHeight: 1.5,
                        }}
                      >
                        "{cleanEvidence(comp.evidence)}"
                      </Typography>
                    )}

                    {comp.explanation && (
                      <Typography
                        variant="caption"
                        sx={{ color: "#444", display: "block", lineHeight: 1.4 }}
                      >
                        {comp.explanation}
                      </Typography>
                    )}
                  </Box>
                ))}
            </AccordionDetails>
          </Accordion>
        );
      })}
    </Box>
  );
}
