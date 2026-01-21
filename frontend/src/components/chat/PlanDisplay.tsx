'use client';

import { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  IconButton,
  Collapse,
  Chip,
} from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import EditIcon from '@mui/icons-material/Edit';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { ExecutionPlan, PlanPhase, PlanTask } from '@/lib/types';

interface PlanDisplayProps {
  plan: ExecutionPlan;
  onApprove: () => void;
  onUpdate: (plan: ExecutionPlan) => void;
}

export function PlanDisplay({ plan, onApprove, onUpdate }: PlanDisplayProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedPlan, setEditedPlan] = useState<ExecutionPlan>(plan);
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(
    new Set(plan.phases.map((p) => p.id))
  );

  const handleSaveEdit = () => {
    onUpdate(editedPlan);
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditedPlan(plan);
    setIsEditing(false);
  };

  const togglePhase = (phaseId: string) => {
    const newExpanded = new Set(expandedPhases);
    if (newExpanded.has(phaseId)) {
      newExpanded.delete(phaseId);
    } else {
      newExpanded.add(phaseId);
    }
    setExpandedPhases(newExpanded);
  };

  const updatePhase = (phaseId: string, updates: Partial<PlanPhase>) => {
    setEditedPlan({
      ...editedPlan,
      phases: editedPlan.phases.map((p) =>
        p.id === phaseId ? { ...p, ...updates } : p
      ),
    });
  };

  const updateTask = (phaseId: string, taskId: string, name: string) => {
    setEditedPlan({
      ...editedPlan,
      phases: editedPlan.phases.map((p) =>
        p.id === phaseId
          ? {
              ...p,
              tasks: p.tasks.map((t) => (t.id === taskId ? { ...t, name } : t)),
            }
          : p
      ),
    });
  };

  const addTask = (phaseId: string) => {
    const phase = editedPlan.phases.find((p) => p.id === phaseId);
    if (!phase) return;
    
    const newTask: PlanTask = {
      id: `task-${Date.now()}`,
      name: 'New task',
      status: 'pending',
    };
    
    updatePhase(phaseId, { tasks: [...phase.tasks, newTask] });
  };

  const removeTask = (phaseId: string, taskId: string) => {
    const phase = editedPlan.phases.find((p) => p.id === phaseId);
    if (!phase) return;
    
    updatePhase(phaseId, { tasks: phase.tasks.filter((t) => t.id !== taskId) });
  };

  const addPhase = () => {
    const newPhase: PlanPhase = {
      id: `phase-${Date.now()}`,
      name: 'New phase',
      tasks: [{ id: `task-${Date.now()}`, name: 'New task', status: 'pending' }],
      status: 'pending',
    };
    setEditedPlan({
      ...editedPlan,
      phases: [...editedPlan.phases, newPhase],
    });
    setExpandedPhases(new Set([...Array.from(expandedPhases), newPhase.id]));
  };

  const removePhase = (phaseId: string) => {
    setEditedPlan({
      ...editedPlan,
      phases: editedPlan.phases.filter((p) => p.id !== phaseId),
    });
  };

  const displayPlan = isEditing ? editedPlan : plan;
  const totalTasks = displayPlan.phases.reduce((sum, p) => sum + p.tasks.length, 0);

  return (
    <Paper
      elevation={0}
      sx={{
        mt: 2,
        p: 2,
        bgcolor: 'background.paper',
        borderRadius: 2,
        border: '2px solid',
        borderColor: 'primary.main',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
        <Box>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Execution Plan
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {displayPlan.phases.length} phases • {totalTasks} tasks
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          {isEditing ? (
            <>
              <Button
                size="small"
                variant="outlined"
                startIcon={<CloseIcon />}
                onClick={handleCancelEdit}
              >
                Cancel
              </Button>
              <Button
                size="small"
                variant="contained"
                startIcon={<CheckIcon />}
                onClick={handleSaveEdit}
              >
                Save
              </Button>
            </>
          ) : (
            <>
              <Button
                size="small"
                variant="outlined"
                startIcon={<EditIcon />}
                onClick={() => setIsEditing(true)}
              >
                Edit
              </Button>
              <Button
                size="small"
                variant="contained"
                color="success"
                startIcon={<PlayArrowIcon />}
                onClick={onApprove}
              >
                Start
              </Button>
            </>
          )}
        </Box>
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
        {displayPlan.phases.map((phase, phaseIndex) => (
          <Box
            key={phase.id}
            sx={{
              bgcolor: 'action.hover',
              borderRadius: 1,
              overflow: 'hidden',
            }}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                p: 1.5,
                cursor: 'pointer',
              }}
              onClick={() => !isEditing && togglePhase(phase.id)}
            >
              {isEditing && (
                <DragIndicatorIcon sx={{ color: 'text.disabled', fontSize: 18 }} />
              )}
              
              <Chip
                label={phaseIndex + 1}
                size="small"
                sx={{
                  minWidth: 24,
                  height: 24,
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                  fontWeight: 600,
                }}
              />

              {isEditing ? (
                <TextField
                  value={phase.name}
                  onChange={(e) => updatePhase(phase.id, { name: e.target.value })}
                  size="small"
                  variant="standard"
                  sx={{ flexGrow: 1 }}
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <Typography variant="subtitle2" sx={{ flexGrow: 1, fontWeight: 500 }}>
                  {phase.name}
                </Typography>
              )}

              <Typography variant="caption" color="text.secondary">
                {phase.tasks.length} tasks
              </Typography>

              {isEditing ? (
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    removePhase(phase.id);
                  }}
                  sx={{ color: 'error.main' }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              ) : (
                <IconButton size="small" sx={{ color: 'text.secondary' }}>
                  {expandedPhases.has(phase.id) ? (
                    <ExpandLessIcon fontSize="small" />
                  ) : (
                    <ExpandMoreIcon fontSize="small" />
                  )}
                </IconButton>
              )}
            </Box>

            <Collapse in={expandedPhases.has(phase.id) || isEditing}>
              <Box sx={{ px: 2, pb: 1.5, pt: 0 }}>
                {phase.tasks.map((task, taskIndex) => (
                  <Box
                    key={task.id}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                      py: 0.5,
                      pl: 4,
                    }}
                  >
                    <Typography
                      variant="caption"
                      sx={{ color: 'text.disabled', minWidth: 20 }}
                    >
                      {phaseIndex + 1}.{taskIndex + 1}
                    </Typography>

                    {isEditing ? (
                      <>
                        <TextField
                          value={task.name}
                          onChange={(e) => updateTask(phase.id, task.id, e.target.value)}
                          size="small"
                          variant="standard"
                          sx={{ flexGrow: 1, '& input': { fontSize: '0.875rem' } }}
                        />
                        <IconButton
                          size="small"
                          onClick={() => removeTask(phase.id, task.id)}
                          sx={{ color: 'error.main', p: 0.25 }}
                        >
                          <DeleteIcon sx={{ fontSize: 16 }} />
                        </IconButton>
                      </>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        {task.name}
                      </Typography>
                    )}
                  </Box>
                ))}

                {isEditing && (
                  <Button
                    size="small"
                    startIcon={<AddIcon />}
                    onClick={() => addTask(phase.id)}
                    sx={{ ml: 4, mt: 0.5 }}
                  >
                    Add task
                  </Button>
                )}
              </Box>
            </Collapse>
          </Box>
        ))}

        {isEditing && (
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={addPhase}
            sx={{ mt: 1 }}
          >
            Add phase
          </Button>
        )}
      </Box>
    </Paper>
  );
}
