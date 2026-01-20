# ReAct Agent Frontend

A modern Next.js frontend for the ReAct Agent with real-time WebSocket communication.

## Features

- Real-time streaming of agent thoughts, actions, and observations
- Terminal-like output display for command execution
- File preview with syntax highlighting
- Session management (create, resume, delete)
- Interrupt capability during agent processing
- Beautiful dark theme with Material UI

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Backend API running on port 8000

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
npm run build
npm start
```

## Architecture

```
src/
├── app/                 # Next.js App Router
│   ├── layout.tsx       # Root layout with theme
│   ├── page.tsx         # Main chat page
│   └── globals.css      # Global styles
├── components/
│   ├── chat/            # Chat UI components
│   ├── agent/           # Agent visualization
│   └── session/         # Session management
├── hooks/               # React hooks
│   ├── useWebSocket.ts  # WebSocket connection
│   ├── useAgent.ts      # Agent state
│   └── useSession.ts    # Session management
├── lib/
│   ├── api.ts           # API client
│   └── types.ts         # TypeScript types
└── theme/
    └── theme.ts         # Material UI theme
```

## WebSocket Protocol

### Client Messages

```typescript
{ type: "chat", content: string }      // Send message
{ type: "interrupt" }                   // Stop processing
{ type: "suggestion", content: string } // Send suggestion
```

### Server Messages

```typescript
{ type: "connected", session_id: string }
{ type: "thought", content: string }
{ type: "action", tool: string, params: object }
{ type: "observation", content: string }
{ type: "final_answer", content: string }
{ type: "error", message: string }
{ type: "interrupted" }
```
