'use client';

import { Paper, Typography, Stack, Box, Stepper, Step, StepLabel, StepContent } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import PlayCircleIcon from '@mui/icons-material/PlayCircle';

interface PlanStep {
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
}

interface PlanDisplayProps {
  steps: PlanStep[];
  title?: string;
}

export function PlanDisplay({ steps, title = 'Plan' }: PlanDisplayProps) {
  const activeStep = steps.findIndex((s) => s.status === 'in_progress');

  return (
    <Paper
      sx={{
        p: 2,
        bgcolor: 'background.paper',
        border: '1px solid',
        borderColor: 'primary.dark',
      }}
    >
      <Typography variant="subtitle1" fontWeight={600} mb={2} color="primary">
        {title}
      </Typography>

      <Stepper activeStep={activeStep === -1 ? steps.length : activeStep} orientation="vertical">
        {steps.map((step, index) => (
          <Step key={index} completed={step.status === 'completed'}>
            <StepLabel
              StepIconComponent={() => {
                if (step.status === 'completed') {
                  return <CheckCircleIcon color="success" />;
                }
                if (step.status === 'in_progress') {
                  return <PlayCircleIcon color="primary" />;
                }
                return <RadioButtonUncheckedIcon color="disabled" />;
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  color:
                    step.status === 'completed'
                      ? 'success.main'
                      : step.status === 'in_progress'
                      ? 'primary.main'
                      : 'text.secondary',
                  fontWeight: step.status === 'in_progress' ? 600 : 400,
                }}
              >
                {step.description}
              </Typography>
            </StepLabel>
          </Step>
        ))}
      </Stepper>
    </Paper>
  );
}
