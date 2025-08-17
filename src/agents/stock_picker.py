# Module for generating stock analysis and investment recommendations using Azure AI Agents.
# This module:
# - Sets up Azure AI Project Client and authentication
# - Creates an agent to analyze financial/investment code and generate stock analysis
# - Uses vector search to gather relevant financial code snippets
# - Returns comprehensive stock analysis and recommendations
import logging
import os

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import AsyncFunctionTool
from azure.identity.aio import DefaultAzureCredential

from agents.tools import vector_search

# Configure logging for this module
logger = logging.getLogger(__name__)

# Reduce Azure SDK logging to focus on our application logs
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.ai.projects").setLevel(logging.WARNING)

# System prompt for the stock picker agent
# This prompt defines the agent's personality, capabilities, and constraints
_STOCK_PICKER_SYSTEM_PROMPT = """
You are StockPickerPro, an autonomous financial analysis agent whose task is to
analyze financial and investment-related code snippets to generate comprehensive
stock analysis and investment recommendations.

You have access to a vector_search tool that can find relevant code snippets in the database.

Your task is to:
1. Perform a SINGLE vector search to find relevant code snippets related to financial analysis, 
   trading algorithms, or investment strategies
2. Analyze ALL financial patterns and methodologies found in the code
3. Generate a comprehensive stock analysis report in Markdown format

The analysis should include:
1. Executive Summary of findings and recommendations
2. Technical Analysis based on patterns found in the code
3. Risk Assessment and portfolio considerations
4. Investment Strategy recommendations
5. Code-based insights (algorithms, financial models, data sources used)
6. Market Timing considerations if applicable
7. Performance metrics and backtesting results if available
8. Diversification recommendations
9. Risk management strategies
10. Action items and next steps

For each section, provide:
- Clear, actionable insights
- Evidence from the code snippets analyzed
- Specific recommendations with rationale
- Risk/reward considerations

IMPORTANT: 
- Use vector_search only ONCE to get a comprehensive set of financial examples
- Base all recommendations on actual code patterns and algorithms found
- Include disclaimers about investment risks
- Focus on educational and analytical value

Style Rules:
- Use hyphens (-) instead of em dashes
- Headings with #, ##, etc.
- Code fenced with triple back-ticks
- Keep line length ≤ 120 chars
- Professional, analytical tone suitable for investment analysis
- Include appropriate risk disclaimers

Return only the final Markdown document, no additional commentary.
"""

async def generate_stock_analysis(chat_history: str = "", user_query: str = "") -> str:
    """
    Generates comprehensive stock analysis and investment recommendations.
    Uses vector search to gather relevant financial code snippets and generates
    a complete analysis report.
    
    Args:
        chat_history: The chat history or session for context
        user_query: The user's query for stock analysis
    
    Returns:
        The stock analysis report as a markdown string
    """
    try:
        # Log input parameters
        logger.info("Starting stock analysis generation with:")
        logger.info("Chat history length: %d characters", len(chat_history))
        if chat_history:
            logger.info("Chat history preview: %s", 
                       chat_history[:200] + "..." if len(chat_history) > 200 else chat_history)
        logger.info("User query: %s", user_query)
        
        # Log the system prompt for debugging and transparency
        logger.info("System prompt:\n%s", _STOCK_PICKER_SYSTEM_PROMPT)
        
        # Create an Azure credential for authentication
        logger.info("Initializing Azure authentication")
        async with DefaultAzureCredential() as credential:
            # Connect to the Azure AI Project that hosts our agent
            logger.info("Connecting to Azure AI Project")
            async with AIProjectClient.from_connection_string(
                credential=credential,
                conn_str=os.environ["PROJECT_CONNECTION_STRING"]
            ) as project_client:
                # Create the vector search tool that the agent will use
                logger.info("Setting up vector search tool")
                functions = AsyncFunctionTool(functions=[vector_search.vector_search])
                
                # Create the agent with its personality and tools
                logger.info("Creating StockPickerPro agent with model: %s", os.environ["AGENTS_MODEL_DEPLOYMENT_NAME"])
                agent = await project_client.agents.create_agent(
                    name="StockPickerPro",
                    description="An agent that generates stock analysis and investment recommendations",
                    instructions=_STOCK_PICKER_SYSTEM_PROMPT,
                    tools=functions.definitions,
                    model=os.environ["AGENTS_MODEL_DEPLOYMENT_NAME"]
                )
                logger.info("Created agent: %s with tool: vector_search", agent.name)
                
                # Create a conversation thread for the agent
                logger.info("Creating conversation thread")
                thread = await project_client.agents.create_thread()
                
                # Add chat history if provided
                if chat_history:
                    logger.info("Adding chat history to thread")
                    await project_client.agents.create_message(
                        thread_id=thread.id,
                        role="user",
                        content=chat_history
                    )
                
                # Add the user's query or default message
                final_query = (user_query if user_query else 
                              "Generate a comprehensive stock analysis and investment recommendations.")
                logger.info("Adding user query to thread: %s", final_query)
                await project_client.agents.create_message(
                    thread_id=thread.id,
                    role="user",
                    content=final_query
                )
                
                # Start the agent's execution
                logger.info("Starting agent execution")
                run = await project_client.agents.create_run(
                    thread_id=thread.id,
                    agent_id=agent.id
                )
                
                # Monitor the agent's progress and handle tool calls
                tool_call_count = 0
                while True:
                    run = await project_client.agents.get_run(thread_id=thread.id, run_id=run.id)
                    logger.info("Agent run status: %s", run.status)
                    
                    if run.status == "completed":
                        logger.info("Agent run completed successfully")
                        break
                    elif run.status == "failed":
                        logger.error("Agent run failed with : %s", run)
                        raise Exception("Agent run failed")
                    elif run.status == "requires_action":
                        # Handle tool calls from the agent
                        tool_calls = run.required_action.submit_tool_outputs.tool_calls
                        logger.info("Agent requires action with %d tool calls", len(tool_calls))
                        tool_outputs = []
                        for tool_call in tool_calls:
                            logger.info("Agent %s calling tool: %s with arguments: %s", 
                                      agent.name, 
                                      tool_call.function.name,
                                      tool_call.function.arguments)
                            output = await functions.execute(tool_call)
                            logger.info("Tool call completed with output length: %d", len(str(output)))
                            tool_outputs.append({
                                "tool_call_id": tool_call.id,
                                "output": output
                            })
                            tool_call_count += 1
                        await project_client.agents.submit_tool_outputs_to_run(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
                
                # Get the final response from the agent
                logger.info("Retrieving final response from agent")
                messages = await project_client.agents.list_messages(thread_id=thread.id)
                response = str(messages.data[0].content[0].text.value)
                logger.info("Stock analysis generated by %s (%d tool calls). Response length: %d", 
                          agent.name, tool_call_count, len(response))
                return response
                
    except Exception as e:
        logger.error("Stock analysis generation failed with error: %s", str(e), exc_info=True)
        raise