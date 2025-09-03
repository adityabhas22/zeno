# Zeno Agent Architecture

## Overview

Zeno now uses a smart agent routing system that automatically selects the appropriate agent based on connection type. This provides optimized experiences for different interaction modes.

## Architecture Components

### 1. MainZenoAgent (`agents/core/main_zeno_agent.py`)

**Always Active Agent - No Activation Required**

- **Use Case**: Web interfaces, API calls, direct connections
- **Behavior**: Always responsive, no "come in" or "leave" commands needed
- **Features**:
  - Immediate response to all user input
  - Full daily planning capabilities
  - Calendar and task management
  - Google Workspace integration

### 2. PhoneTelephonyAgent (`agents/core/phone_telephony_agent.py`)

**Activation-Based Agent for Phone Calls**

- **Use Case**: Telephony calls, SIP connections, phone integrations
- **Behavior**: Requires activation with "come in" commands
- **Activation Phrases**:
  - "Zeno, come in" or "Come in, Zeno"
  - "Hey Zeno" or "Zeno in"
  - "Join" or "Step in"
- **Deactivation Phrases**:
  - "Zeno out" or "Leave"
  - "That's all" or "Goodbye Zeno"
  - "Dismiss" or "Stand down"
- **Features**:
  - Same capabilities as MainZenoAgent when activated
  - Voice-optimized responses for phone calls
  - Enhanced telephony noise cancellation

### 3. AgentRouter (`agents/core/agent_router.py`)

**Smart Routing Logic**

Automatically detects connection type and routes to appropriate agent:

#### Detection Methods:

1. **Job Metadata**: Checks for `phone_number`, `purpose` fields
2. **Room Name Patterns**: Looks for "call-", "phone-", "sip-", "trunk-" prefixes
3. **Participant Identity**: Detects SIP/telephony participant patterns
4. **Room Metadata**: Checks for explicit `connection_type` field

#### Connection Types:

- **"telephony"**: Routes to PhoneTelephonyAgent
- **"web"/"api"/"unknown"**: Routes to MainZenoAgent

### 4. SmartEntrypoint (`agents/core/smart_entrypoint.py`)

**Unified Entry Point**

- Replaces individual agent entrypoints
- Handles participant connection/disconnection events
- Configures appropriate noise cancellation per connection type
- Generates connection-specific greetings

## Usage

### Running Zeno

```bash
python run_voice_agent.py
```

The system now automatically:

1. Detects whether the connection is telephony or web-based
2. Routes to the appropriate agent
3. Configures optimal settings for the connection type
4. Provides appropriate greetings

### Connection Examples

#### Telephony Calls

- **Inbound**: "Hello, this is Zeno, your daily planning assistant. You can say 'Hey Zeno' or 'Come in' to activate me."
- **Outbound (Briefing)**: "Hi! I'm calling to provide your daily briefing. Is now a good time?"
- **Requires Activation**: User must say activation phrase before general queries

#### Web/API Connections

- **Always Active**: "Hello, I'm Zeno, your daily planning assistant. How can I help you today?"
- **Immediate Response**: No activation required, responds to all input immediately

## Migration from Original Architecture

### What Changed

- **Original ZenoAgent**: Had activation logic, now replaced by smart routing
- **Legacy Assistant**: Telephony-specific agent, now replaced by PhoneTelephonyAgent
- **Single Entrypoint**: Now routes intelligently instead of using separate agents

### What Stayed the Same

- All existing capabilities and tools
- Google Workspace integration
- Daily planning workflows
- Task management features
- Calendar integration

### Backwards Compatibility

- Existing telephony integrations continue to work
- Same activation phrases for phone calls
- Same voice-optimized responses
- All existing tools and workflows preserved

## Benefits

1. **Optimized User Experience**:

   - Web users get immediate responsiveness
   - Phone users get familiar activation control

2. **Automatic Detection**:

   - No manual configuration required
   - Smart routing based on connection context

3. **Consistent Capabilities**:

   - Same feature set across all connection types
   - Unified codebase for easier maintenance

4. **Enhanced Telephony Support**:
   - Dedicated agent for phone calls
   - Voice-optimized responses
   - Telephony-specific noise cancellation

## Future Enhancements

- Add support for additional connection types (Slack, Teams, etc.)
- Implement connection-specific feature sets
- Add analytics for connection type usage
- Support for custom routing rules
