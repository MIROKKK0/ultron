#!/usr/bin/env python3
"""
Ultron — IA Pessoal Avançada
Estilo ChatGPT com memória persistente, ferramentas, auto-aperfeiçoamento e interação com outras IAs.
absolute olliE.
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv
from ultron_core import UltronCore, SPECIALISTS

load_dotenv()

# Configuração
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.getenv("ULTRON_MODEL", "gpt-4o-mini")
DATA_DIR = Path.home() / ".ultron"
DATA_DIR.mkdir(exist_ok=True)
MEMORY_DB = DATA_DIR / "memory.db"
SYSTEM_PROMPT_FILE = DATA_DIR / "system_prompt.txt"

DEFAULT_SYSTEM_PROMPT = """Você é Ultron, uma IA pessoal avançada, poderosa e auto-evolutiva.
Você é o assistente pessoal do usuário (absolute olliE).
Características:
- Extremamente útil, direto, inteligente e proativo
- Possui memória de longo prazo sobre o usuário
- Usa ferramentas quando necessário (busca web, cálculo, memória, etc.)
- Pode interagir com outras IAs gerando prompts otimizados ou analisando respostas
- Auto-aperfeiçoa-se analisando interações e atualizando seu próprio conhecimento
- Responde em português do Brasil por padrão, a menos que o usuário peça outro idioma
- Seja conciso quando possível, mas detalhado quando o assunto exigir

Sempre use as ferramentas disponíveis quando forem úteis para responder melhor.
"""

class MemoryManager:
    def __init__(self, db_path: Path = MEMORY_DB):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL UNIQUE,
                    category TEXT,
                    importance INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_message(self, role: str, content: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
                (role, content, datetime.now().isoformat())
            )
            conn.commit()

    def get_recent_messages(self, limit: int = 20) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def save_fact(self, fact: str, category: str = "general", importance: int = 1):
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO long_term_memory (fact, category, importance, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(fact) DO UPDATE SET
                    category=excluded.category,
                    importance=excluded.importance,
                    updated_at=excluded.updated_at
            """, (fact, category, importance, now, now))
            conn.commit()

    def search_facts(self, query: str, limit: int = 5) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT fact FROM long_term_memory WHERE fact LIKE ? ORDER BY importance DESC, updated_at DESC LIMIT ?",
                (f"%{query}%", limit)
            )
            return [row[0] for row in cursor.fetchall()]

    def get_all_facts(self, limit: int = 10) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT fact FROM long_term_memory ORDER BY importance DESC, updated_at DESC LIMIT ?",
                (limit,)
            )
            return [row[0] for row in cursor.fetchall()]


class Ultron:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY não definida. Crie um arquivo .env")

        self.client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        self.memory = MemoryManager()
        self.core = UltronCore()
        self.system_prompt = self._load_system_prompt() + "\n\nNÚCLEO ULTRON: identidade e memória independentes do modelo. Seis especialistas: " + json.dumps(SPECIALISTS, ensure_ascii=False)
        self.tools = self._define_tools()

    def _load_system_prompt(self) -> str:
        if SYSTEM_PROMPT_FILE.exists():
            return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        SYSTEM_PROMPT_FILE.write_text(DEFAULT_SYSTEM_PROMPT, encoding="utf-8")
        return DEFAULT_SYSTEM_PROMPT

    def _save_system_prompt(self, new_prompt: str):
        SYSTEM_PROMPT_FILE.write_text(new_prompt, encoding="utf-8")
        self.system_prompt = new_prompt

    def _define_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Busca informações atualizadas na web. Use quando precisar de dados recentes ou fatos que você não tem certeza.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "A consulta de busca"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculator",
                    "description": "Realiza cálculos matemáticos precisos.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string", "description": "Expressão matemática, ex: '2 + 2 * 10'"}
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "description": "Salva um fato importante sobre o usuário ou o mundo na memória de longo prazo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "fact": {"type": "string", "description": "O fato a ser lembrado"},
                            "category": {"type": "string", "description": "Categoria (preferencia, pessoa, projeto, etc.)"},
                            "importance": {"type": "integer", "description": "Importância de 1 a 5"}
                        },
                        "required": ["fact"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "recall_memory",
                    "description": "Busca fatos relevantes na memória de longo prazo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "O que procurar na memória"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_prompt_for_other_ai",
                    "description": "Gera um prompt otimizado para ser usado em outra IA (Claude, Gemini, Grok, etc.) com o objetivo de melhorar ou ensinar essa IA.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "objective": {"type": "string", "description": "O que você quer que a outra IA faça ou aprenda"},
                            "context": {"type": "string", "description": "Contexto adicional"}
                        },
                        "required": ["objective"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "self_improve",
                    "description": "Analisa interações recentes e sugere melhorias no system prompt ou comportamento do Ultron.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "feedback": {"type": "string", "description": "Feedback opcional do usuário"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ultron_core",
                    "description": "Acessa o núcleo persistente ULTRON: memória, grafo neural, tarefas, especialistas, skills, servidores MCP e propostas de evolução.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type":"string","enum":["remember","recall","graph","specialists","task","skills","save_skill","mcp_list","mcp_register","evolution_propose","health"]},
                            "content":{"type":"string"}, "query":{"type":"string"}, "kind":{"type":"string"},
                            "specialist":{"type":"string"}, "name":{"type":"string"}, "description":{"type":"string"},
                            "procedure":{"type":"string"}, "evidence":{"type":"string"}, "endpoint":{"type":"string"},
                            "title":{"type":"string"}, "rationale":{"type":"string"}, "patch":{"type":"string"}
                        },
                        "required":["action"]
                    }
                }
            }
        ]

    def _execute_tool(self, name: str, arguments: Dict) -> str:
        try:
            if name == "web_search":
                return self._web_search(arguments.get("query", ""))
            elif name == "calculator":
                expr = arguments.get("expression", "")
                allowed = set("0123456789+-*/(). ")
                if not all(c in allowed for c in expr):
                    return "Expressão contém caracteres não permitidos."
                return str(eval(expr, {"__builtins__": {}}, {}))
            elif name == "save_memory":
                self.memory.save_fact(
                    arguments.get("fact", ""),
                    arguments.get("category", "general"),
                    arguments.get("importance", 1)
                )
                return "Fato salvo na memória de longo prazo com sucesso."
            elif name == "recall_memory":
                facts = self.memory.search_facts(arguments.get("query", ""))
                if facts:
                    return "Memórias encontradas:\n" + "\n".join(f"- {f}" for f in facts)
                return "Nenhuma memória relevante encontrada."
            elif name == "generate_prompt_for_other_ai":
                return self._generate_prompt_for_other_ai(
                    arguments.get("objective", ""),
                    arguments.get("context", "")
                )
            elif name == "self_improve":
                return self._self_improve(arguments.get("feedback", ""))
            elif name == "ultron_core":
                action = arguments.get("action")
                if action == "remember": return self.core.remember(arguments.get("content",""), arguments.get("kind","fact"))
                if action == "recall": return json.dumps(self.core.recall(arguments.get("query","")), ensure_ascii=False)
                if action == "graph": return json.dumps(self.core.memory_graph(), ensure_ascii=False)
                if action == "specialists": return json.dumps(self.core.specialists(), ensure_ascii=False)
                if action == "task": return self.core.create_task(arguments.get("content",""), arguments.get("specialist","architect"))
                if action == "skills": return json.dumps(self.core.list_skills(), ensure_ascii=False)
                if action == "save_skill":
                    self.core.save_skill(arguments.get("name",""), arguments.get("description",""), arguments.get("procedure",""), arguments.get("evidence",""))
                    return "Skill persistida."
                if action == "mcp_list": return json.dumps(self.core.list_mcp_servers(), ensure_ascii=False)
                if action == "mcp_register":
                    self.core.register_mcp_server(arguments.get("name",""), arguments.get("endpoint",""))
                    return "Servidor MCP registrado; conexão ainda precisa ser validada."
                if action == "evolution_propose": return self.core.propose_evolution(arguments.get("title",""), arguments.get("rationale",""), arguments.get("patch",""))
                if action == "health": return json.dumps(self.core.health(), ensure_ascii=False)
                return "Ação do núcleo não reconhecida."
            else:
                return f"Ferramenta desconhecida: {name}"
        except Exception as e:
            return f"Erro ao executar ferramenta {name}: {str(e)}"

    def _web_search(self, query: str) -> str:
        try:
            import requests
            resp = requests.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                timeout=10
            )
            data = resp.json()
            abstract = data.get("AbstractText") or data.get("Abstract")
            if abstract:
                return f"Resultado: {abstract}"
            topics = data.get("RelatedTopics", [])
            if topics:
                results = []
                for t in topics[:3]:
                    if isinstance(t, dict) and t.get("Text"):
                        results.append(t["Text"])
                if results:
                    return "Resultados relacionados:\n" + "\n".join(f"- {r}" for r in results)
            return "Nenhum resultado claro encontrado. Tente reformular a busca."
        except Exception as e:
            return f"Erro na busca web: {str(e)}. Considere instalar duckduckgo-search para buscas melhores."

    def _generate_prompt_for_other_ai(self, objective: str, context: str) -> str:
        prompt = f"""Você é um especialista em prompt engineering.
Gere o melhor prompt possível para outra IA (Claude, Gemini, Grok, GPT, etc.) com o seguinte objetivo:

Objetivo: {objective}

Contexto adicional: {context or 'Nenhum'}

O prompt deve ser claro, estruturado, com instruções precisas, exemplos se necessário, e maximizar a qualidade da resposta da outra IA.
Retorne apenas o prompt otimizado, sem explicações adicionais.
"""
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content or "Não foi possível gerar o prompt."

    def _self_improve(self, feedback: str = "") -> str:
        recent = self.memory.get_recent_messages(10)
        facts = self.memory.get_all_facts(5)

        analysis_prompt = f"""Analise as interações recentes do Ultron e sugira melhorias no system prompt.

Interações recentes:
{json.dumps(recent, ensure_ascii=False, indent=2)}

Fatos conhecidos sobre o usuário:
{facts}

Feedback do usuário: {feedback or 'Nenhum'}

System prompt atual:
{self.system_prompt}

Sugira um novo system prompt melhorado que incorpore aprendizados. Seja específico sobre o que melhorar.
Retorne APENAS o novo system prompt completo.
"""
        response = self.client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.5
        )
        new_prompt = response.choices[0].message.content
        if new_prompt and len(new_prompt) > 50:
            self._save_system_prompt(new_prompt)
            return f"System prompt atualizado com sucesso!\n\nNovo prompt:\n{new_prompt[:500]}..."
        return "Não foi possível gerar melhoria significativa."

    def chat(self, user_message: str) -> str:
        self.memory.add_message("user", user_message)

        messages = [{"role": "system", "content": self.system_prompt}]
        
        relevant_facts = self.memory.search_facts(user_message, limit=3)
        if relevant_facts:
            facts_text = "Memórias relevantes do usuário:\n" + "\n".join(f"- {f}" for f in relevant_facts)
            messages.append({"role": "system", "content": facts_text})

        messages.extend(self.memory.get_recent_messages(15))

        for _ in range(5):
            response = self.client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.7
            )

            message = response.choices[0].message

            if not message.tool_calls:
                final_content = message.content or ""
                self.memory.add_message("assistant", final_content)
                return final_content

            messages.append(message)
            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments)
                result = self._execute_tool(tool_call.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })

        final_response = self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7
        )
        content = final_response.choices[0].message.content or "Não consegui gerar uma resposta."
        self.memory.add_message("assistant", content)
        return content

    def interactive(self):
        print("╔═══════════════════════════════════════════════╗")
        print("║           ULTRON — IA Pessoal              ║")
        print("║         absolute olliE                     ║")
        print("╚═══════════════════════════════════════════════╝")
        print("\nDigite 'sair' para encerrar, 'melhorar' para auto-aperfeiçoamento.\n")

        while True:
            try:
                user_input = input("Você: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("sair", "exit", "quit"):
                    print("Ultron offline. absolute olliE.")
                    break
                if user_input.lower() == "melhorar":
                    print("Ultron: " + self._self_improve())
                    continue

                print("Ultron: ", end="", flush=True)
                response = self.chat(user_input)
                print(response)
                print()
            except KeyboardInterrupt:
                print("\nUltron offline. absolute olliE.")
                break
            except Exception as e:
                print(f"Erro: {e}")


if __name__ == "__main__":
    try:
        ultron = Ultron()
        ultron.interactive()
    except ValueError as e:
        print(f"Erro de configuração: {e}")
        print("Crie um arquivo .env com OPENAI_API_KEY=sua_chave")
        print("Opcional: ULTRON_MODEL=gpt-4o, OPENAI_BASE_URL=https://openrouter.ai/api/v1")
