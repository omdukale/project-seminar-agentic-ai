<h1> project-seminar-agentic-ai </h1>
<h2> Legal Research AI Assistant, an agentic AI mini-project. </h2>
<br>
This is an agentic AI project that I created as a part of my project seminar in my 2nd year of engineering at IIT BBS.
<br>
I have created a legal research AI assistant which consists of an agentic workflow as follows : 
<br><br>
RAG Retrieval → Contextual Answering → Web Cross-Check → Final Output
<br>
The way this works is, the first agent retrieves relevant information to the query from the documents provided to it by using RAG. 
<br>
The next agent will then answer the original query based on the context provided by the previous agent.
<br>
Finally, the last agent will analyse that answer and perform web search using the perplexity-ask mcp server to verify if all the information is up to date.
<br><br>
I've made use of the OpenAI Agents SDK toolkit to create these agents and used OpenAI Assistants API to implement RAG. 
The documentation for which you can find at <href> https://platform.openai.com/docs/assistants/tools/file-search </href> and <href> https://platform.openai.com/docs/guides/agents-sdk
