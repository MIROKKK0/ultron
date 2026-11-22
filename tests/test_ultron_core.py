import tempfile, unittest
from pathlib import Path
from ultron_core import UltronCore, SPECIALISTS
class CoreTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.core=UltronCore(Path(self.tmp.name)/"core.db")
 def tearDown(self):self.tmp.cleanup()
 def test_identity_and_specialists(self):
  self.assertEqual(self.core.recall("ULTRON")[0]["kind"],"identity"); self.assertEqual(len(SPECIALISTS),6)
 def test_memory_graph(self):
  a=self.core.remember("Projeto ULTRON","project"); b=self.core.remember("Memória persistente","architecture"); self.core.link_memories(a,b,"supports")
  self.assertEqual(len(self.core.memory_graph()["nodes"]),3); self.assertEqual(self.core.memory_graph()["edges"][0]["relation"],"supports")
 def test_semantic_recall_ranks_relevant_memories(self):
  unrelated=self.core.remember("Receita de bolo de chocolate","note",5)
  relevant=self.core.remember("ULTRON usa memória semântica persistente","architecture",2)
  results=self.core.recall("memória semântica",limit=5)
  self.assertEqual(results[0]["id"],relevant)
  self.assertNotIn(unrelated,[item["id"] for item in results])
 def test_task_loop(self):
  self.core.create_task("Revisar arquitetura","architect"); self.assertEqual(self.core.task_loop(lambda task:"revisado")[0]["status"],"completed")
 def test_skills_and_mcp(self):
  self.core.save_skill("testar","Testes","Executar unittest","CI verde"); self.assertEqual(self.core.list_skills()[0]["name"],"testar")
  self.core.register_mcp_server("local","https://mcp.example.com"); self.assertEqual(len(self.core.list_mcp_servers()),1)
 def test_evolution_gate(self):
  p=self.core.propose_evolution("Melhoria","Razão","diff",.8); self.assertEqual(self.core.evaluate_evolution(p,.9,False),"rejected")
  p=self.core.propose_evolution("Melhoria 2","Razão","diff",.8); self.assertEqual(self.core.evaluate_evolution(p,.9,True),"eligible_for_review")
  p=self.core.propose_evolution("Regressão","Razão","diff",.8); self.assertEqual(self.core.evaluate_evolution(p,.7,True),"rejected")
if __name__=="__main__":unittest.main()
