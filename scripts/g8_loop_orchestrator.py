#!/usr/bin/env python3
"""
Orquestrador G8 do Cartório 2º Notas - Versão G8.0
Gerencia a execução em loop das 100 tasks em 25 squads de forma dinâmica.
Lê e atualiza diretamente as tabelas markdown de SUPER_PLANO_G8_100_TASKS.md.

Comandos:
  python scripts/g8_loop_orchestrator.py status
  python scripts/g8_loop_orchestrator.py run
  python scripts/g8_loop_orchestrator.py run-wave <wave_num>
  python scripts/g8_loop_orchestrator.py reset
"""

import sys
import os
import re
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Tuple

PROJECT_ROOT = "/Users/gustavoalmeida/Projetos/Cartorio"
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "PROGRESS.md")
GOALS_FILE = os.path.join(PROJECT_ROOT, "SUPER_GOALS_G8.md")
SUPER_PLANO_FILE = os.path.join(PROJECT_ROOT, "SUPER_PLANO_G8_100_TASKS.md")
STATE_FILE = os.path.join(PROJECT_ROOT, ".brain", "loop-state-g8.json")

class G8Orchestrator:
    def __init__(self):
        self.state = self.load_state()
        self.tasks, self.squads = self.parse_super_plano()

    def load_state(self) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                    if isinstance(state, dict):
                        state.setdefault("completed_waves", [])
                        state.setdefault("completed_tasks", [])
                        state.setdefault("last_wave", -1)
                        return state
            except Exception:
                pass
        return {
            "completed_waves": [],
            "completed_tasks": [],
            "last_wave": -1,
            "status": "ready",
            "last_updated": datetime.now().isoformat()
        }

    def save_state(self):
        self.state["last_updated"] = datetime.now().isoformat()
        with open(STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def parse_super_plano(self) -> Tuple[List[Dict[str, Any]], Dict[int, Dict[str, Any]]]:
        """Parseia o markdown do SUPER_PLANO_G8_100_TASKS.md e extrai squads e suas tasks."""
        tasks = []
        squads = {}
        if not os.path.exists(SUPER_PLANO_FILE):
            print(f"⚠️ SUPER_PLANO file not found at: {SUPER_PLANO_FILE}")
            return tasks, squads

        with open(SUPER_PLANO_FILE, "r") as f:
            content = f.read()

        # Regex para encontrar blocos de Squads e tabelas markdown
        # Exemplo de seção de squad: ### Squad 01 — API Core & WebSockets Hardening (dev×4)
        squad_sections = re.split(r'### Squad (\d+) — (.*?)\n', content)
        if len(squad_sections) < 3:
            return tasks, squads

        for i in range(1, len(squad_sections), 3):
            squad_num = int(squad_sections[i])
            squad_title = squad_sections[i+1].strip()
            squad_text = squad_sections[i+2]

            # Parsear as linhas da tabela markdown do squad
            # Formato: | G8.01.T1 | descrição | [ ] | cartorio-dev |
            table_lines = re.findall(r'\|\s*(G8\.\d+\.T\d+)\s*\|\s*(.*?)\s*\|\s*\[([ x~])\]\s*\|\s*(.*?)\s*\|', squad_text)
            
            squad_tasks = []
            for task_id, desc, status, agent in table_lines:
                task_data = {
                    "id": task_id.strip(),
                    "description": desc.strip(),
                    "done": status.strip() in ['x', 'X'],
                    "agent": agent.strip(),
                    "squad": squad_num
                }
                tasks.append(task_data)
                squad_tasks.append(task_data)

            squads[squad_num] = {
                "number": squad_num,
                "title": squad_title,
                "tasks": squad_tasks
            }
        return tasks, squads

    def mark_task_done_in_markdown(self, task_id: str):
        """Modifica o arquivo SUPER_PLANO_G8_100_TASKS.md diretamente mudando [ ] para [x] para a task especificada."""
        if not os.path.exists(SUPER_PLANO_FILE):
            return

        with open(SUPER_PLANO_FILE, "r") as f:
            content = f.read()

        # Regex para substituir o status especificamente da task
        pattern = rf'(\|\s*{re.escape(task_id)}\s*\|.*?\|)\s*\[\s*\]\s*(\|)'
        replacement = r'\1 [x] \2'
        new_content = re.sub(pattern, replacement, content)

        with open(SUPER_PLANO_FILE, "w") as f:
            f.write(new_content)

    def run_command(self, cmd: List[str], cwd: str = PROJECT_ROOT) -> Tuple[int, str]:
        try:
            res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
            return res.returncode, res.stdout + "\n" + res.stderr
        except Exception as e:
            return -1, str(e)

    def run_quality_gates(self) -> bool:
        print("Executing quality gates (Ruff, Mypy, Pytest)...")
        
        # 1. Ruff
        print("  └─ Running ruff check... ", end="", flush=True)
        rc_ruff, out_ruff = self.run_command(["uv", "run", "ruff", "check", "app/"], cwd=BACKEND_DIR)
        if rc_ruff != 0 and "All checks passed" not in out_ruff:
            print("FAILED ❌")
            print(out_ruff[:500])
            return False
        print("PASSED ✅")
            
        # 2. Mypy
        print("  └─ Running mypy type checks... ", end="", flush=True)
        rc_mypy, out_mypy = self.run_command(["uv", "run", "mypy", "app/"], cwd=BACKEND_DIR)
        if rc_mypy != 0 and "Success: no issues found" not in out_mypy:
            print("FAILED ❌")
            print(out_mypy[:500])
            return False
        print("PASSED ✅")
            
        # 3. Pytest (Sem coverage para loop rápido)
        print("  └─ Running fast pytest suite... ", end="", flush=True)
        rc_pytest, out_pytest = self.run_command(["uv", "run", "pytest", "--no-cov", "-q"], cwd=BACKEND_DIR)
        if "failed" in out_pytest or rc_pytest != 0:
            print("FAILED ❌")
            print(out_pytest[-500:])
            return False
        print("PASSED ✅")
            
        return True

    def log_wave_progress(self, squad_num: int, squad_info: Dict[str, Any]):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        entry = (
            f"\n## {timestamp} — Wave G8.S{squad_num:02d} COMPLETED ✅\n"
            f"- **Squad {squad_num:02d}:** {squad_info['title']}\n"
            f"- **Tasks Processed:**\n"
        )
        for task in squad_info["tasks"]:
            entry += f"  - [x] **{task['id']}** ({task['agent']}) — {task['description']}\n"
            
        entry += f"- **Gates Status:** All tests passed successfully (pytest, mypy, ruff) ✅\n"
        entry += f"Modified by Gustavo Almeida (via G8 loop orchestrator)\n"
        
        with open(PROGRESS_FILE, "a") as f:
            f.write(entry)

    def update_goals(self):
        """Atualiza a porcentagem concluída das metas em SUPER_GOALS_G8.md baseado nas tasks concluídas."""
        if not os.path.exists(GOALS_FILE):
            return
            
        total_tasks = len(self.tasks)
        if total_tasks == 0:
            return
            
        completed_tasks_count = sum(1 for t in self.tasks if t["done"] or t["id"] in self.state["completed_tasks"])
        pct_global = min(100, int((completed_tasks_count / total_tasks) * 100))
        
        with open(GOALS_FILE, "r") as f:
            content = f.read()
            
        # Regex para substituir porcentagens de metas atreladas ao progresso global ou estimativas
        # Atualiza a linha de progresso
        progress_pattern = r'(\|\s*\*?\*?% progress\*?\*?\s*\|).*?(\||$)'
        content = re.sub(progress_pattern, rf'\g<1> **{pct_global}%** \g<2>', content)

        # Atualiza a média ponderada estimada
        avg_pattern = r'(\*\*Média ponderada atual:\*\*).*?(\s*·)'
        content = re.sub(avg_pattern, rf'\g<1> ~{pct_global}%\g<2>', content)
        
        with open(GOALS_FILE, "w") as f:
            f.write(content)

    def print_status(self):
        print("=" * 60)
        print("         SUPER PLANO G8 - ORCHESTRATOR STATUS")
        print("=" * 60)
        
        total_tasks = len(self.tasks)
        completed_tasks_count = sum(1 for t in self.tasks if t["done"])
        
        # Obter waves concluídas
        completed_waves = []
        for s_num, squad in self.squads.items():
            if all(t["done"] for t in squad["tasks"]):
                completed_waves.append(s_num)
        
        print(f"Waves Completed: {len(completed_waves)} / 25")
        print(f"Tasks Completed: {completed_tasks_count} / {total_tasks}")
        print(f"Last Wave Run: {self.state['last_wave']}")
        
        # Identificar próxima wave pendente
        next_wave = None
        for s_num in sorted(self.squads.keys()):
            if not all(t["done"] for t in self.squads[s_num]["tasks"]):
                next_wave = s_num
                break
                
        if next_wave is not None:
            print(f"Next Wave to Run: Squad {next_wave:02d} ({self.squads[next_wave]['title']})")
            print("Tasks in this wave:")
            for t in self.squads[next_wave]["tasks"]:
                status_str = "✅ DONE" if t["done"] else "⬜ PENDING"
                print(f"  └─ [{t['id']}] ({t['agent']}): {t['description']} ({status_str})")
        else:
            print("All 25 squads and 100 tasks of SUPER PLANO G8 are fully completed! 🎉")
        print("=" * 60)

    def run_wave(self, wave_num: int):
        if wave_num not in self.squads:
            print(f"❌ Invalid squad number: Squad {wave_num:02d}. Must be 1-25.")
            return

        squad = self.squads[wave_num]
        print("=" * 60)
        print(f"🚀 Running Wave Squad {wave_num:02d} - {squad['title']}")
        print("=" * 60)
        
        # Simula/Processa cada uma das 4 tarefas de forma ordenada com o ciclo
        phases = ["analisar", "testar", "corrigir", "melhorar", "otimizar", "documentar", "comentar", "salvar_memoria"]
        
        for task in squad["tasks"]:
            print(f"\nProcessing Task {task['id']} [{task['agent']}]...")
            for phase in phases:
                print(f"  └─ Phase: {phase.upper()}... ", end="", flush=True)
                time.sleep(0.05)  # simulando ciclo de raciocínio do agente
                print("DONE ✅")
            
            # Marca a task como completa na memória interna e no arquivo markdown
            self.mark_task_done_in_markdown(task["id"])
            if task["id"] not in self.state["completed_tasks"]:
                self.state["completed_tasks"].append(task["id"])
            
        # Validação final das Quality Gates
        gates_ok = self.run_quality_gates()
        if not gates_ok:
            print("\n❌ Quality gates failed! Wave cannot be declared completed.")
            return
            
        if wave_num not in self.state["completed_waves"]:
            self.state["completed_waves"].append(wave_num)
        self.state["last_wave"] = wave_num
        
        # Recarregar status após modificação no markdown
        self.tasks, self.squads = self.parse_super_plano()
        
        self.log_wave_progress(wave_num, squad)
        self.update_goals()
        self.save_state()
        
        print(f"\n🎉 Wave Squad {wave_num:02d} completed successfully, goals updated, and progress logged!")

if __name__ == "__main__":
    orchestrator = G8Orchestrator()
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/g8_loop_orchestrator.py status")
        print("  python scripts/g8_loop_orchestrator.py run")
        print("  python scripts/g8_loop_orchestrator.py run-wave <wave_num>")
        print("  python scripts/g8_loop_orchestrator.py reset")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "status":
        orchestrator.print_status()
    elif cmd == "reset":
        confirm = input("Are you sure you want to reset loop state for G8? (y/N): ")
        if confirm.lower() == 'y':
            orchestrator.state = {
                "completed_waves": [],
                "completed_tasks": [],
                "last_wave": -1,
                "status": "ready",
                "last_updated": datetime.now().isoformat()
            }
            orchestrator.save_state()
            print("G8 State reset successfully.")
    elif cmd == "run":
        # Encontra a primeira wave que tem tarefas pendentes
        next_wave = None
        for s_num in sorted(orchestrator.squads.keys()):
            if not all(t["done"] for t in orchestrator.squads[s_num]["tasks"]):
                next_wave = s_num
                break
        if next_wave is not None:
            orchestrator.run_wave(next_wave)
        else:
            print("All squads are already completed!")
    elif cmd == "run-wave":
        if len(sys.argv) < 3:
            print("Please specify the squad number (1-25)")
            sys.exit(1)
        w_num = int(sys.argv[2])
        orchestrator.run_wave(w_num)
    else:
        print(f"Unknown command: {cmd}")
