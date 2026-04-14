# Phase 9: Multi-Turn Conversations - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers multi-turn NPC conversation management: ConversationManager tracks active conversations per NPC, LLM classifies dialogue acts (greeting/question/command/farewell/statement), conversations are paused gracefully during combat/loot interruptions and resumed on return to calm, and completed conversations are LLM-summarized and stored in Phase 6's long-term memory.

</domain>

<decisions>
## Implementation Decisions

### Conversation State Model
- Conversation data: `{npc_name, topic, turns [{speaker, text, act}], status (active/paused/complete), started_at}`
- Unlimited concurrent conversations tracked by NPC name — matches "multiple concurrent without confusion"
- NPC detection: colon pattern in MUD output (`"NPC says: ..."`) + maintained NPC name list — automatic
- ConversationManager class following GoalManager/PreferenceManager pattern — consistent architecture

### Dialogue Act Detection
- LLM classifies each NPC message into act type — flexible, handles MUD text variety
- 5 dialogue act types: greeting, question, command, farewell, statement
- NPC detected via colon pattern in MUD output + maintained NPC name list
- Dialogue act stored per turn and used by LLM for context-appropriate responses — dual purpose

### Interruption Handling
- Interruption detected by activity change in MUD output (combat/loot keywords) — leverages Phase 6 activity detection
- Conversation paused in memory with last_topic preserved — ready to resume
- Resumption: agent detects return to calm, re-injects conversation context into next prompt
- Paused conversation expiry: 10 minutes (configurable) — prevents stale ghost conversations

### Conversation Storage & Summary
- Conversation completed on: farewell dialogue act detected OR idle 5 minutes — dual trigger
- LLM generates completion summary: "Spoke with [NPC] about [topic], agreed to [outcome]"
- Completed conversations stored in ContextManager's `long_term_memory` (Phase 6) — direct integration
- Keep last 50 completed conversations, pruned by age — bounded storage

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- GoalManager and PreferenceManager patterns — class structure to follow for ConversationManager
- Phase 6 ContextManager: `long_term_memory` list, `_detect_activity()` method — integrate directly
- `llm_agent.py` play loop — integration point for NPC detection and conversation updates
- `build_prompt()` — extend with active conversation context
- WebSocket broadcast pattern — for conversation_update events

### Established Patterns
- Dataclass-based models with JSON serialization (GoalManager, PreferenceManager)
- Async WebSocket handlers in mud_client.py
- LLM for intelligent classification (Phase 7 subgoal generation, Phase 8 preference inference)
- Activity detection already in ContextManager (combat/exploration/conversation/idle)

### Integration Points
- `ContextManager._detect_activity()` — reuse activity detection for interruption detection
- `ContextManager.long_term_memory` — destination for completed conversation summaries
- `llm_agent.py` play loop — detect NPC messages in MUD output each cycle
- `build_prompt()` — inject active conversation state: "Currently talking to [NPC] about [topic]"
- `mud_client.py` — add get_conversations WebSocket command

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches within the decided framework.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>
