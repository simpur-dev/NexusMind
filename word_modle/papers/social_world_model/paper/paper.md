
From Individual to Society: A Survey on Social Simulation Driven by Large Language Model-based Agents • 27
8.3 Society Simulation
Despite considerable progress in society simulation using LLM-driven agents, current approaches face several
key challenges. (1) Alignment with real world remains limited. Many studies simply observe agent behaviors
within constructed environments without ensuring alignment with real and dynamic social contexts, including
realistic population composition and interaction mechanisms [281 ]. As a result, it is unclear whether their conclu-
sions have practical signiicance. Although some work tries to address alignment in speciic social scenarios, such
as social networks and economic models [ 56, 116 ], these eforts are constrained by data sparsity, incompleteness,
and noise, making it diicult to verify whether agent populations truly replicate human social dynamics. (2)
Scaling up to large populations and more complex interactions currently requires partial simpliications of
the simulation [ 39, 68, 148 ]. While this trade-of is necessary for feasibility, determining how to minimize the
sacriice of simulation idelity remains an open challenge. (3) LLM interpretability poses another diiculty:
the black-box nature of LLMs makes it hard to provide rigorous causal explanations for individual behaviors or
collective outcomes, and developing more transparent and robust approaches at the intersection of LLMs and
social science remains a critical research problem.
8.4 Trade-ofs and mutual promotion between diferent levels
When advancing from individual to scenario and society simulations, researchers face inherent trade-ofs between
idelity and scalability. Thus, micro-level studies prioritize idelity, while large-scale evaluations emphasize
scalability, with both requiring basic practical feasibility, such as computational eiciency, data availability, and
calibration reliability, before optimizing another dimension. Recent work on lightweight personalized preference
modeling [ 17, 115 ] has proposed adapter-based approaches that enhance scalability while preserving idelity. In
contrast, for large-scale societal simulations, strict individual alignment, though beneicial, is not always critical
for obtaining valid macroscopic outcomes. Large-scale experiments further suggest that moderate individual-level
noise can be tolerated as long as aggregate patterns remain reliable, although interpretations should be carefully
bounded to avoid overextending conclusions beyond the simulation’s scope [236].
Beyond trade-ofs, the three levels can also mutually reinforce each other. Individual simulation forms the
foundation: enhancing a model’s general task-solving and role-playing abilities often improves the efectiveness
of scenario and large-scale societal simulations [61, 199 ]. In turn, scenario simulations provide diverse and
challenging environments, where interactive feedback fosters individual learning [ 13 , 215 ] and improve the
individual model’s ability to achieve goals in the scenarios. Finally, societal simulations reveal behavioral patterns
and crowd wisdom, which can further guide proile rewriting at the individual level and coordination strategies
in scenario-based group interactions.
9 Conclusion
In this paper, we categorize LLM-driven social simulations into three types: individual, scenario, and society
simulation, highlighting their progression from modeling individual behaviors to replicating complex social
dynamics. By systematically reviewing architectures, methods, and evaluations across these categories, we
provide a structured framework for advancing research in this ield. This work aims to guide the development
of LLM-based simulations and foster interdisciplinary studies to address real-world challenges and support
decision-making.
Acknowledgments
The work was supported by the AI for Science Program, Shanghai Municipal Commission of Economy and
Informatization (Grant Nos. 2025-GZL-RGZN-BTBX-02028) and the CFFF platform of Fudan University.
ACM Comput. Surv.
28 • X. Mou et al.
References
[1] Mahyar Abbasian et al. 2024. Conversational Health Agents: A Personalized LLM-Powered Agent Framework. arxiv:2310.02374 (2024).
[2] Harsh Agrawal et al . 2023. Multimodal Persona Based Generation of Comic Dialogs. In Proc. Annu. Meeting Assoc. Comput. Linguistics.
14150ś14164.
[3] Gati V Aher et al . 2023. Using large language models to simulate multiple humans and replicate human subject studies. In Proc. Int.
Conf. Mach. Learn. 337ś371.
[4] Jaewoo Ahn et al. 2023. MPCHAT: Towards Multimodal Persona-Grounded Conversation. In Proc. Annu. Meeting Assoc. Comput.
Linguistics. 3354ś3377.
[5] Gertrude Elizabeth Margaret Anscombe. 1956. Intention. In Proceedings of the Aristotelian Society, Vol. 57. JSTOR, 321ś332.
[6] Argyle et al. 2023. Out of One, Many: Using Language Models to Simulate Human Samples. Political Analysis 31, 3 (2023), 337ś351.
[7] Mohammadmehdi Ataei et al . 2024. Elicitron: An LLM Agent-Based Simulation Framework for Design Requirements Elicitation.
arXiv:2404.16045 (2024).
[8] Robert Axelrod. 1997. The dissemination of culture: A model with local convergence and global polarization. Journal of Conlict
Resolution 41, 2 (1997), 203ś226. [new] Cultural dissemination model showing polarization emergence.
[9] Jinheon Baek et al . 2024. Knowledge-augmented large language models for personalized contextual query suggestion. In Proc. of the
ACM on Web Conf. 3355ś3366.
[10] Jinheon Baek et al. 2024. Researchagent: Iterative research idea generation over scientiic literature with large language models.
arXiv:2404.07738 (2024).
[11] Bai et al . 2022. Training a helpful and harmless assistant with reinforcement learning from human feedback. arXiv:2204.05862 (2022).
[12] Zachary R Baker et al. 2024. Simulating The US Senate: An LLM-Driven Agent Approach to Modeling Legislative Behavior and
Bipartisanship. arXiv:2406.18702 (2024).
[13] Zhijie Bao et al. 2024. PIORS: Personalized Intelligent Outpatient Reception based on Large Language Model with Multi-Agents Medical
Scenario Simulation. arXiv:2411.13902 (2024).
[14] Marcel Binz et al. 2024. Turning large language models into cognitive models. In Proc. Int. Conf. Learn. Representations.
[15] Eric Bonabeau. 2002. Agent-based modeling: Methods and techniques for simulating human systems. Proceedings of the national
academy of sciences 99, suppl_3 (2002), 7280ś7287.
[16] Angana Borah et al. 2025. Mind the (Belief) Gap: Group Identity in the World of LLMs. arXiv:2503.02016 (2025).
[17] Avinandan Bose et al. 2025. LoRe: Personalizing LLMs via Low-Rank Reward Modeling. arXiv:2504.14439 (2025).
[18] Faeze Brahman et al. 2021. łLet Your Characters Tell Their Storyž: A Dataset for Character-Centric Narrative Understanding. In Proc.
Conf. Empirical Methods Natural Lang. Process. Finding. 1734ś1752.
[19] Jinyu Cai et al . 2024. Language Evolution for Evading Social Media Regulation via LLM-Based Multi-Agent Simulation. In Proc. IEEE
Congr. Evolutionary Comput. 1ś10.
[20] Emilio Calvano, Giacomo Calzolari, Vincenzo Denicolò, and Sergio Pastorello. 2020. Artiicial intelligence, algorithmic pricing, and
collusion. American Economic Review 110, 10 (2020), 3267ś3297. [new] Q-learning based ABM for market dynamics.
[21] Erica Cau et al. 2025. Language-Driven Opinion Dynamics in Agent-Based Simulations with LLMs. arXiv:2502.19098 (2025).
[22] Mert Cemri et al. 2025. Why do multi-agent llm systems fail? arXiv:2503.13657 (2025).
[23] Chi Ming Chan et al. 2023. Chateval: Towards better LLM-based evaluators through multi-agent debate. arXiv:2308.07201 (2023).
[24] Yaqub Chaudhary et al. 2024. Large Language Models as Instruments of Power: New Regimes of Autonomous Manipulation and
Control. arXiv:2405.03813 (2024).
[25] Kushal Chawla et al . 2023. Be Selish, But Wisely: Investigating the Impact of Agent Personality in Mixed-Motive Human-Agent
Interactions. arXiv:2310.14404 (2023).
[26] Chen et al. 2023. Large Language Models Meet Harry Potter: A Dataset for Aligning Dialogue Agents with Characters. In Proc. Conf.
Empirical Methods Natural Lang. Process. 8506ś8520.
[27] Guangyao Chen et al. 2024. Autoagents: A framework for automatic agent generation. In Proc. Int. Joint Conf. Artif. Intell. 22ś30.
[28] Hongzhan Chen et al. 2024. Socialbench: Sociality evaluation of role-playing conversational agents. In Proc. Annu. Meeting Assoc.
Comput. Linguistics Finding. 2108ś2126.
[29] Jiangjie Chen et al. 2024. From persona to personalization: A survey on role-playing language agents. arXiv:2404.18231 (2024).
[30] Jiaqi Chen et al. 2024. S-Agents: self-organizing agents in open-ended environment. arXiv:2402.04578 (2024).
[31] W. Chen et al. 2024. Agentverse: Facilitating Multi-Agent Collaboration and Exploring Emergent Behaviors. In Proc. Int. Conf. Learn.
Representations.
[32] Weize Chen et al . 2024. Beyond Natural Language: LLMs Leveraging Alternative Formats for Enhanced Reasoning and Communication.
In Proc. Conf. Empirical Methods Natural Lang. Process. Findings. 10626ś10641.
[33] Weize Chen et al. 2024. Optima: Optimizing Efectiveness and Eiciency for LLM-Based Multi-Agent System. arXiv:2410.08115 (2024).
ACM Comput. Surv.
From Individual to Society: A Survey on Social Simulation Driven by Large Language Model-based Agents • 29
[34] Yongchao Chen et al. 2024. Scalable multi-robot collaboration with large language models: Centralized or decentralized systems?. In
IEEE Int. Conf. Robotics and Automation. IEEE, 4311ś4317.
[35] Zhipeng Chen et al. 2023. ChatCoT: Tool-Augmented Chain-of-Thought Reasoning on Chat-based Large Language Models. In Proc.
Conf. Empirical Methods Natural Lang. Process. 14777ś14790.
[36] Myra Cheng et al . 2023. Marked Personas: Using Natural Language Prompts to Measure Stereotypes in Language Models. In Proc.
Annu. Meeting Assoc. Comput. Linguistics. 1504ś1532.
[37] Cho et al. 2022. A personalized dialogue generator with implicit user persona detection. arXiv:2204.07372 (2022).
[38] Won Ik Cho et al. 2023. When crowd meets persona: Creating a large-scale open-domain persona dialogue corpus. arXiv:2304.00350
(2023).
[39] Ayush Chopra et al. 2024. On the limits of agency in agent-based models. arXiv:2409.10568 (2024).
[40] Yun-Shiuan Chuang et al. 2023. Computational agent-based models in opinion dynamics: A survey on social simulations and empirical
studies. arXiv:2306.03446 (2023).
[41] Yun-Shiuan Chuang et al. 2024. Beyond Demographics: Aligning Role-playing LLM-based Agents Using Human Belief Networks. In
Proc. Conf. Empirical Methods Natural Lang. Process. Finding. 14010ś14026.
[42] Yun-Shiuan Chuang et al. 2024. Simulating Opinion Dynamics with Networks of LLM-based Agents. In Proc. Annu. Meeting Assoc.
Comput. Linguistics Finding. 3326ś3346.
[43] Yun-Shiuan Chuang et al. 2024. The Wisdom of Partisan Crowds: Comparing Collective Intelligence in Humans and LLM-based Agents.
In Proc. of the Ann. Meet. of the Cog. Sci.e Soc., Vol. 46.
[44] Yanqi Dai et al . 2024. MMRole: A Comprehensive Framework for Developing and Evaluating Multimodal Role-Playing Agents.
arXiv:2408.04203 (2024).
[45] Mike D’Arcy et al. 2024. Marg: Multi-agent review generation for scientiic papers. arXiv:2401.04259 (2024).
[46] Ameet Deshpande et al. 2023. Toxicity in chatgpt: Analyzing persona-assigned language models. arXiv:2304.05335 (2023).
[47] Yihong Dong et al. 2024. Self-Collaboration Code Generation via ChatGPT. ACM Trans. Softw. Eng. Methodol. 33, 7 (2024), 1ś38.
[48] Silin Du et al. 2024. Helmsman of the Masses? Evaluate the Opinion Leadership of Large Language Models in the Werewolf Game. In
Conf. on Lang. Model.
[49] Yilun Du et al. 2024. Improving Factuality and Reasoning in Language Models through Multiagent Debate. In Proc. Int. Conf. Mach.
Learn.
[50] Joshua M Epstein et al. 1996. Growing artiicial societies: social science from the bottom up. Brookings Institution Press.
[51] Zhihao Fan et al . 2024. Ai hospital: Interactive evaluation and collaboration of llms as intern doctors for clinical diagnosis.
arXiv:2402.09742 (2024).
[52] Nicholas Farn et al. 2023. Tooltalk: Evaluating tool-usage in a conversational setting. arXiv:2311.10775 (2023).
[53] Xiachong Feng et al. 2025. Reasoning does not necessarily improve role-playing ability. arXiv:2502.16940 (2025).
[54] Nicoló Fontana et al . 2024. Nicer Than Humans: How do Large Language Models Behave in the Prisoner’s Dilemma? arXiv:2406.13605
(2024).
[55] Yao Fu et al. 2023. Improving language model negotiation with self-play and in-context learning from ai feedback. arXiv:2305.10142
(2023).
[56] C. Gao et al. 2023. S3: Social-Network Simulation System with Large Language Model-Empowered Agents. arXiv:2307.14984 (2023).
[57] Chen Gao et al . 2024. Large language models empowered agent-based modeling and simulation: A survey and perspectives. Humanities
and Social Sciences Communications 11, 1 (2024), 1ś24.
[58] Dawei Gao et al. 2024. Agentscope: A lexible yet robust multi-agent platform. arXiv:2402.14034 (2024).
[59] Jingsheng Gao et al. 2023. LiveChat: A large-scale personalized dialogue dataset automatically constructed from live streaming.
arXiv:2306.08401 (2023).
[60] Zhaolin Gao et al. 2024. Reviewer2: Optimizing Review Generation Through Prompt Generation. arXiv:2402.10886 (2024).
[61] Tao Ge et al. 2024. Scaling synthetic data creation with 1,000,000,000 personas. arXiv:2406.20094 (2024).
[62] Zorik Gekhman et al . 2023. On the robustness of dialogue history representation in conversational question answering: a comprehensive
study and a new prompt-based method. Trans. Assoc. Comput. Linguist. 11 (2023), 351ś366.
[63] R. Gong et al . 2024. MindAgent: Emergent Gaming Interaction. In Proc. Conf. North Amer. Chapter Assoc. Comput. Linguistics Findings.
3154ś3183.
[64] Mark S Granovetter. 1973. The strength of weak ties. Ame. jour. of soc. 78, 6 (1973), 1360ś1380.
[65] Kai Greshake et al . 2023. More than you’ve asked for: A comprehensive analysis of novel prompt injection threats to application-
integrated large language models. arXiv:2302.12173 27 (2023).
[66] Chenhao Gu et al. 2025. Large Language Model Driven Agents for Simulating Echo Chamber Formation. arXiv:2502.18138 (2025).
[67] Xiangming Gu et al . 2024. Agent smith: A single image can jailbreak one million multimodal llm agents exponentially fast.
arXiv:2402.08567 (2024).
[68] Haoxiang Guan et al. 2025. Modeling Earth-Scale Human-Like Societies with One Billion Agents. arXiv:2506.12078 (2025).
ACM Comput. Surv.
30 • X. Mou et al.
[69] Shangmin Guo et al. 2024. Economics arena for large language models. arXiv:2401.01735 (2024).
[70] Taicheng Guo et al. 2024. Large language model based multi-agents: A survey of progress and challenges. In Proc. Int. Joint Conf. Artif.
Intell. Survey Track. 8048ś8057.
[71] Wei Guo et al . 2021. Detecting emergent intersectional biases: Contextualized word embeddings contain a distribution of human-like
biases. In Proceedings of the 2021 AAAI/ACM Conference on AI, Ethics, and Society. 122ś133.
[72] Sil Hamilton. 2023. Blind judgement: Agent-based supreme court modelling with gpt. arXiv:2301.05327 (2023).
[73] Lewis Hammond et al. 2025. Multi-agent risks from advanced ai. arXiv preprint arXiv:2502.14143 (2025).
[74] X. Han et al . 2023. "Guinea Pig Trials" Utilizing GPT: A Novel Smart Agent-Based Modeling Approach for Studying Firm Competition
and Collusion. arXiv:2308.10974 (2023).
[75] Rui Hao et al. 2023. Chatllm network: More brains, more intelligence. arXiv:2304.12998 (2023).
[76] Jochen Hartmann et al . 2023. The political ideology of conversational AI: Converging evidence on ChatGPT’s pro-environmental,
left-libertarian orientation. arXiv:2301.01768 (2023).
[77] Md Mahadi Hassan et al. 2023. Chatgpt as your personal data scientist. arXiv:2305.13657 (2023).
[78] Zhitao He et al . 2024. AgentsCourt: Building Judicial Decision-Making Agents with Court Debate Simulation and Legal Knowledge
Augmentation. In Proc. Conf. Empirical Methods Natural Lang. Process. Finding. 9399ś9416.
[79] Rainer Hegselmann et al. 2005. Opinion dynamics driven by various ways of averaging. Com. Econ. 25 (2005), 381ś405.
[80] Rainer Hegselmann and Ulrich Krause. 2002. Opinion dynamics and bounded conidence models, analysis, and simulation. Journal of
Artiicial Societies and Social Simulation 5, 3 (2002). [new] Bounded conidence model for continuous opinion dynamics.
[81] Dirk Helbing. 2012. Social self-organization: Agent-based simulations and experiments to study emergent social behavior. Springer.
[82] Sirui Hong et al. 2024. MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework. In Proc. Int. Conf. Learn. Representa-
tions.
[83] John J Horton. 2023. Large language models as simulated economic agents: What can we learn from homo silicus? Technical Report.
National Bureau of Economic Research.
[84] Wenyue Hua et al . 2023. War and peace (waragent): Large language model-based multi-agent simulation of world wars. arXiv:2311.17227
(2023).
[85] Jiangyong Huang et al. 2023. An embodied generalist agent in 3d world. arXiv:2311.12871 (2023).
[86] Jen-tse Huang et al . 2024. Apathetic or Empathetic? Evaluating LLMs’ Emotional Alignments with Humans. In Advances in Neural
Information Processing Systems 37.
[87] Xu Huang et al . 2023. Recommender ai agent: Integrating large language models for interactive recommendations. arXiv:2308.16505
(2023).
[88] Pegah Jandaghi et al . 2023. Faithful persona-based conversational dataset generation with large language models. arXiv:2312.10007
(2023).
[89] Jang et al. 2022. Call for customized conversation: Customized conversation grounding persona and knowledge. Proc. of the AAAI Conf.
on Arti. Intel. 36, 10 (2022), 10803ś10812.
[90] Joel Jang et al. 2023. Personalized soups: Personalized large language model alignment via post-hoc parameter merging. arXiv:2310.11564
(2023).
[91] Daniel Jarrett et al . 2023. Language agents as digital representatives in collective decision-making. In Proc. Int. Conf. Neural Inf. Process.
Syst. Workshop.
[92] Jiarui Ji et al . 2024. SRAP-Agent: Simulating and Optimizing Scarce Resource Allocation Policy with LLM-based Agent. In Proc. Conf.
Empirical Methods Natural Lang. Process. 267ś293.
[93] Ziwei Ji et al. 2023. Survey of hallucination in natural language generation. ACM computing surveys 55, 12 (2023), 1ś38.
[94] Jingru Jia et al . 2025. Large Language Model Strategic Reasoning Evaluation through Behavioral Game Theory. arXiv:2502.20432 (2025).
[95] Jiang et al. 2024. Evaluating and inducing personality in pre-trained language models. Proc. Int. Conf. Neural Inf. Process. Syst. 36 (2024).
[96] Mingyu Jin et al . 2024. What if LLMs Have Diferent World Views: Simulating Alien Civilizations with LLM-based Agents.
arXiv:2402.13184 (2024).
[97] Yiqiao Jin et al. 2024. AgentReview: Exploring Peer Review Dynamics with LLM Agents. In Proc. Conf. Empirical Methods Natural Lang.
Process. 1208ś1226.
[98] Zhao Kaiya et al. 2023. Lyfe agents: Generative agents for low-cost real-time social interactions. arXiv:2310.02172 (2023).
[99] Saketh Reddy Karra et al. 2022. Estimating the Personality of White-Box Language Models. arXiv:2204.12000 (2022).
[100] Daniel Katz et al. 2015. The social psychology of organizations. In Organ. beha. 2. 152ś168.
[101] Takeshi Kojima et al. 2022. Large language models are zero-shot reasoners. Proc. Int. Conf. Neural Inf. Process. Syst. 35 (2022),
22199ś22213.
[102] Chalamalasetti Kranti et al . 2023. clembench: Using Game Play to Evaluate Chat-Optimized Language Models as Conversational
Agents. In Proc. Conf. Empirical Methods Natural Lang. Process. 11174ś11219.
ACM Comput. Surv.
From Individual to Society: A Survey on Social Simulation Driven by Large Language Model-based Agents • 31
[103] Yihuai Lan et al . 2024. LLM-Based Agent Society Investigation: Collaboration and Confrontation in Avalon Gameplay. In Proc. 2024
Conf. Empirical Methods Nat. Lang. Process. 128ś145.
[104] Maik Larooij et al. 2025. Do large language models solve the problems of agent-based modeling? a critical review of generative social
simulations. arXiv:2504.03274 (2025).
[105] Sanguk Lee et al . 2024. Can large language models estimate public opinion about global warming? An empirical assessment of
algorithmic idelity and bias. PLoS Climate 3, 8 (2024), e0000429.
[106] Sanguk Lee et al. 2024. Exploring Social Desirability Response Bias in Large Language Models: Evidence from GPT-4 Simulations.
arXiv:2410.15442 (2024).
[107] Yoon Kyung Lee et al. 2024. Enhancing Empathic Reasoning of Large Language Models Based on Psychotherapy Models for AI-assisted
Social Support. Kor. Jour. of Cog. Sci. (2024).
[108] Cheng Li et al. 2023. ChatHaruhi: Reviving Anime Character in Reality via Large Language Model. ArXiv (2023).
[109] Cheng Li et al. 2024. CulturePark: Boosting Cross-cultural Understanding in Large Language Models. In Proc. Int. Conf. Neural Inf.
Process. Syst.
[110] Guohao Li et al. 2023. CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society. In Proc. Int. Conf.
Neural Inf. Process. Syst., Vol. 36. 51991ś52008.
[111] Jiwei Li et al. 2016. A Persona-Based Neural Conversation Model. In Proc. Annu. Meeting Assoc. Comput. Linguistics. 994ś1003.
[112] Juntao Li et al . 2021. Dialogue history matters! personalized response selection in multi-turn retrieval-based chatbots. ACM Tran. on
Infor, Sys, (TOIS) 39, 4 (2021), 1ś25.
[113] Junyi Li et al. 2023. On the steerability of large language models toward data-driven personas. arXiv:2311.04978 (2023).
[114] Junkai Li et al. 2024. Agent hospital: A simulacrum of hospital with evolvable medical agents. arXiv:2405.02957 (2024).
[115] Jia-Nan Li et al . 2025. From 1,000,000 users to every user: Scaling up personalized preference for user-level alignment. arXiv:2503.15463
(2025).
[116] Nian Li et al. 2024. Econagent: large language model-empowered agents for simulating macroeconomic activities. In Proc. Annu.
Meeting Assoc. Comput. Linguistics. 15523ś15536.
[117] Xingxuan Li et al. 2024. Evaluating psychological safety of large language models. (2024), 1826ś1843.
[118] Xinyi Li et al. 2024. Large Language Model-driven Multi-Agent Simulation for News Difusion Under Diferent Network Structures.
arXiv:2410.13909 (2024).
[119] Xinyi Li, Zhiqiang Guo, Qinglang Guo, Hao Jin, Weizhi Ma, and Min Zhang. 2025. Integrating LLM and Difusion-Based Agents for
Social Simulation. arXiv:2510.16366 [cs.CY] https://arxiv.org/abs/2510.16366
[120] Yang Li et al . 2023. TradingGPT: Multi-agent system with layered memory and distinct characters for enhanced inancial trading
performance. arXiv:2309.03736 (2023).
[121] Yuanchun Li et al. 2024. Personal llm agents: Insights and survey about the capability, eiciency and security. arXiv:2401.05459 (2024).
[122] Yu Li et al. 2025. AgentSwift: Eicient LLM Agent Design via Value-guided Hierarchical Search. arXiv:2506.06017 (2025).
[123] Jingcong Liang et al. 2024. Debatrix: Multi-dimensional Debate Judge with Iterative Chronological Analysis Based on LLM. In Proc.
Annu. Meeting Assoc. Comput. Linguistics Finding. 14575ś14595.
[124] Tian Liang et al . 2023. Leveraging word guessing games to assess the intelligence of large language models. arXiv:2310.20499 (2023).
[125] Tian Liang et al. 2024. Encouraging Divergent Thinking in Large Language Models through Multi-Agent Debate. In Proc. Conf. Empirical
Methods Natural Lang. Process. 17889ś17904.
[126] Tom Lieberum, Matthew Rahtz, János Kramár, Neel Nanda, Geofrey Irving, Rohin Shah, and Vladimir Mikulik. 2023. Does circuit
analysis interpretability scale? evidence from multiple choice capabilities in chinchilla. arXiv preprint arXiv:2307.09458 (2023).
[127] Jonathan Light et al . 2023. From Text to Tactic: Evaluating LLMs Playing the Game of Avalon. In Proc. Int. Conf. Neural Inf. Process. Syst.
Workshop.
[128] Blodgett Su Lin et al. 2020. Language (technology) is power: A critical survey of" bias" in nlp. arXiv:2005.14050 (2020).
[129] Bill Yuchen Lin et al . 2023. SwiftSage: A Generative Agent with Fast and Slow Thinking for Complex Interactive Tasks. In Proc. Int.
Conf. Neural Inf. Process. Syst., Vol. 36.
[130] Jiaju Lin et al. 2023. AgentSims: An Open-Source Sandbox for Large Language Model Evaluation. arXiv:2308.04026 (2023).
[131] Liu et al . 2022. Improving personality consistency in conversation by persona extending. In Proc. ACM Int. Conf. Inf. Knowl. Manag.
1350ś1359.
[132] Junwei Liu et al. 2024. Large Language Model-Based Agents for Software Engineering: A Survey. arXiv:2409.02977 (2024).
[133] Jiahao Liu et al. 2025. Enhancing Cross-Domain Recommendations with Memory-Optimized LLM-Based User Agents. arXiv:2502.13843
(2025).
[134] Wei Liu et al . 2024. Autonomous Agents for Collaborative Task under Information Asymmetry. In Proc. Int. Conf. Neural Inf. Process.
Syst.
[135] Xiao Liu et al. 2023. AgentBench: Evaluating LLMs as Agents. ArXiv (2023).
[136] Yuhan Liu et al . 2024. From a Tiny Slip to a Giant Leap: An LLM-Based Simulation for Fake News Evolution. arXiv:2410.19064 (2024).
ACM Comput. Surv.
32 • X. Mou et al.
[137] Yuhan Liu et al. 2024. From Skepticism to Acceptance: Simulating the Attitude Dynamics Toward Fake News. In Proc. Int. Joint Conf.
Artif. Intell.
[138] Junyu Luo et al. 2025. Large language model agent: A survey on methodology, applications and challenges. arXiv:2503.21460 (2025).
[139] Jie Ma et al . 2024. Debate on Graph: a Flexible and Reliable Reasoning Framework for Large Language Models. arXiv:2409.03155 (2024).
[140] Zhao Mandi et al . 2024. Roco: Dialectic multi-robot collaboration with large language models. In IEEE Int. Conf. Robotics and Automation.
286ś299.
[141] Samuele Marro et al. 2024. A Scalable Communication Protocol for Networks of Large Language Models. arXiv:2410.11905 (2024).
[142] Agnieszka Mensfelt et al . 2024. Logic-Enhanced Language Model Agents for Trustworthy Social Simulations. arXiv:2408.16081 (2024).
[143] Stanley Milgram. 1963. Behavioral study of obedience. The Jour. of abnormal and social psychology 67, 4 (1963), 371.
[144] Marilù Miotto et al. 2022. Who is GPT-3? An exploration of personality, values and demographics. In Proc. Workshop Nat. Lang. Process.
Comput. Soc. Sci. (NLP+CSS). Association for Computational Linguistics, Abu Dhabi, UAE, 218ś227.
[145] Pablo Morales et al . 2025. Multi-agent systems powered by large language models: applications in swarm intelligence. Frontiers in
Artiicial Intelligence 8 (2025), 1593017. [new] LLM+ABM Functional: Integrates LLMs with NetLogo for swarm simulations. LLM for
principle-based decisions, NetLogo rules for movement dynamics..
[146] Xinyi Mou et al . 2024. AgentSense: Benchmarking Social Intelligence of Language Agents through Interactive Scenarios. arXiv:2410.19346
(2024).
[147] Xinyi Mou et al. 2024. Unifying Local and Global Knowledge: Empowering Large Language Models as Political Experts with Knowledge
Graphs. In Proceedings of the ACM on Web Conference 2024. 2603ś2614.
[148] Xinyi Mou et al . 2024. Unveiling the Truth and Facilitating Change: Towards Agent-based Large-scale Social Movement Simulation. In
Proc. Annu. Meeting Assoc. Comput. Linguistics Finding. 4789ś4809.
[149] Xinyi Mou et al. 2025. EcoLANG: Eicient and Efective Agent Communication Language Induction for Social Simulation.
arXiv:2505.06904 (2025).
[150] Mikhail Mozikov et al. 2024. The Good, the Bad, and the Hulk-like GPT: Analyzing Emotional Decisions of Large Language Models in
Cooperation and Bargaining Games. arXiv:2406.03299 (2024).
[151] Varun Nair et al. 2024. DERA: Enhancing Large Language Model Completions with Dialog-Enabled Resolving Agents. In Proc. 6th
Clinical Natural Lang. Process. Workshop. 122ś161.
[152] Mehwish Nasim et al. 2025. Simulating Inluence Dynamics with LLM Agents. arXiv:2503.08709 (2025).
[153] Keyu Pan et al . 2023. Do llms possess a personality? making the mbti test an amazing evaluation for large language models.
arXiv:2307.16180 (2023).
[154] Xuchen Pan et al. 2024. Very Large-Scale Multi-Agent Simulation in AgentScope. arXiv:2407.17789 (2024).
[155] Jeongeon Park et al. 2023. Choicemates: Supporting unfamiliar online decision-making with multi-agent conversational interactions.
arXiv:2310.01331 (2023).
[156] J. S. Park et al. 2022. Social Simulacra: Creating Populated Prototypes for Social Computing Systems. In Proc. 35th Annu. ACM Symp.
User Interface Softw. Technol. 1ś18.
[157] Joon Sung Park et al. 2023. Generative agents: Interactive simulacra of human behavior. In Proc. of the 36th ann. acm sym. on user inter.
soft. and tec. 1ś22.
[158] Joon Sung Park et al. 2024. Generative Agent Simulations of 1,000 People. arXiv:2411.10109 (2024).
[159] Jinghua Piao et al. 2025. AgentSociety: Large-Scale Simulation of LLM-Driven Generative Agents Advances Understanding of Human
Behaviors and Society. arXiv:2502.08691 (2025).
[160] Bhandari Pranav et al. 2025. Can LLM Agents Maintain a Persona in Discourse? arXiv:2502.11843 (2025).
[161] Amin Qasmi et al. 2025. Competing LLM Agents in a Non-Cooperative Game of Opinion Polarisation. arXiv:2502.11649 (2025).
[162] Chen Qian et al. 2024. Chatdev: Communicative agents for software development. In Proc. Annu. Meeting Assoc. Comput. Linguistics.
15174ś15186.
[163] Chen Qian et al. 2024. Experiential co-learning of software-developing agents. In Proc. Annu. Meeting Assoc. Comput. Linguistics.
5628ś5640.
[164] Chen Qian et al. 2024. Iterative Experience Reinement of Software-Developing Agents. arXiv:2405.04219 (2024).
[165] Chen Qian et al. 2024. Scaling Large-Language-Model-based Multi-Agent Collaboration. arXiv:2406.07155 (2024).
[166] Huachuan Qiu et al . 2024. Interactive agents: Simulating counselor-client psychological counseling via role-playing llm-to-llm
interactions. arXiv:2408.15787 (2024).
[167] Zhongyi Qiu et al . 2025. Can LLMs Simulate Social Media Engagement? A Study on Action-Guided Response Generation.
arXiv:2502.12073 (2025).
[168] Yao Qu et al . 2024. Performance and biases of Large Language Models in public opinion simulation. Humanit. Soc. Sci. Commun. 11, 1
(2024), 1ś13.
[169] Le Anh Quang et al. 2018. Agent-based models in social physics. Jour. of the Kor. Phy. Soc. 72 (2018), 1272ś1280.
ACM Comput. Surv.
From Individual to Society: A Survey on Social Simulation Driven by Large Language Model-based Agents • 33
[170] Daking Rai et al. 2024. A practical review of mechanistic interpretability for transformer-based language models. arXiv preprint
arXiv:2407.02646 (2024).
[171] Yiting Ran et al. 2024. Capturing minds, not just words: Enhancing role-playing language models with personality-indicative data.
arXiv:2406.18921 (2024).
[172] Ruiyang Ren et al. 2024. BASES: Large-scale Web Search User Simulation with Large Language Model based Agents. In Proc. Conf.
Empirical Methods Natural Lang. Process. Finding. 902ś917.
[173] Siyue Ren et al . 2024. Emergence of Social Norms in Large Language Model-based Agent Societies. In Proc. Int. Joint Conf. Artif. Intell.
7895ś7903.
[174] Giulio Rossetti et al. 2024. Y Social: an LLM-powered Social Media Digital Twin.
[175] Pouria Rouzrokh et al. 2025. LatteReview: A Multi-Agent Framework for Systematic Review Automation Using Large Language Models.
arXiv:2501.05468 (2025).
[176] Xu Rui et al . 2025. Guess What I am Thinking: A Benchmark for Inner Thought Reasoning of Role-Playing Language Agents.
arXiv:2503.08193 (2025).
[177] Jérôme Rutinowski et al. 2023. The self-perception and political biases of ChatGPT. arXiv:2304.07333 (2023).
[178] Mustafa Safdari et al. 2023. Personality traits in large language models. arXiv:2307.00184 (2023).
[179] Alireza Salemi et al. 2023. Lamp: When large language models meet personalization. arXiv:2304.11406 (2023).
[180] Thomas C Schelling. 1971. Dynamic models of segregation. Jour. of math. soc. 1, 2 (1971), 143ś186.
[181] Oliver Schmitt et al . 2021. CharacterChat: Supporting the Creation of Fictional Characters through Conversation and Progressive
Manifestation with a Chatbot. In Proc, of Conf. on Crea. and Cogn. Article 10, 10 pages.
[182] Eric Schwitzgebel et al. 2024. Creating a large language model of a philosopher. Mind & Language (2024), 237ś259.
[183] Yunfan Shao et al. 2023. Character-LLM: A Trainable Agent for Role-Playing. In Proc. Conf. Empirical Methods Natural Lang. Process.
13153ś13187.
[184] Ryan Shea et al. 2023. Building Persona Consistent Dialogue Agents with Oline Reinforcement Learning. arXiv:2310.10735 (2023).
[185] Tianhao Shen et al. 2023. Roleeval: A bilingual role evaluation benchmark for large language models. arXiv:2312.16132 (2023).
[186] Yongliang Shen et al . 2023. Hugginggpt: Solving ai tasks with chatgpt and its friends in hugging face. Advances in Neural Information
Processing Systems 36 (2023), 38154ś38180.
[187] Zijing Shi et al. 2023. Cooperation on the ly: Exploring language agents for ad hoc teamwork in the avalon game. arXiv:2312.17515
(2023).
[188] Chan Hee Song et al. 2023. Llm-planner: Few-shot grounded planning for embodied agents with large language models. In Proc.
IEEE/CVF Int. Conf. Comput. Vis. 2998ś3009.
[189] Flaminio Squazzoni et al . 2014. Social simulation in the social sciences: A brief overview. Soci. Sci. Comp. Review 32, 3 (2014), 279ś294.
[190] Karthik Sreedhar et al. 2024. Simulating human strategic behavior: Comparing single and multi-agent llms. arXiv:2402.08189 (2024).
[191] Arjun V Sudhakar et al. 2025. A Generalist Hanabi Agent. arXiv:2503.14555 (2025).
[192] Jingyun Sun et al. 2024. LawLuo: A Chinese Law Firm Co-run by LLM Agents. arXiv:2407.16252 (2024).
[193] Linzhuang Sun et al . 2023. Rational sensibility: Llm enhanced empathetic response generation guided by self-presentation theory.
arXiv:2312.08702 (2023).
[194] Libo Sun et al. 2024. Identity-driven hierarchical role-playing agents. arXiv:2407.19412 (2024).
[195] Seungjong Sun et al. 2024. Random Silicon Sampling: Simulating Human Sub-Population Opinion Using a Large Language Model
Based on Group-Level Demographic Information. arXiv:2402.18144 (2024).
[196] R. Suzuki et al . 2024. An Evolutionary Model of Personality Traits Related to Cooperative Behavior Using a Large Language Model.
Scientiic Reports 14, 1 (2024), 5989.
[197] Yashar Talebirad et al. 2023. Multi-agent collaboration: Harnessing the power of intelligent llm agents. arXiv:2306.03314 (2023).
[198] Weihao Tan et al . 2024. True Knowledge Comes from Practice: Aligning Large Language Models with Embodied Environments via
Reinforcement Learning. In Proc. Int. Conf. Learn. Representations.
[199] Shuo Tang et al. 2024. Synthesizing Post-Training Data for LLMs through Multi-Agent Simulation. arXiv:2410.14251 (2024).
[200] Xiangru Tang et al . 2024. MedAgents: Large Language Models as Collaborators for Zero-shot Medical Reasoning. In Proc. Annu. Meeting
Assoc. Comput. Linguistics Finding. 599ś621.
[201] Xiangru Tang et al. 2025. ChemAgent: Self-updating Library in Large Language Models Improves Chemical Reasoning. arXiv:2501.06590
(2025).
[202] Petter Törnberg et al. 2023. Simulating social media using large language models to evaluate alternative news feed algorithms.
arXiv:2310.05984 (2023).
[203] Quan Tu et al. 2024. Charactereval: A chinese benchmark for role-playing conversational agent evaluation. arXiv:2401.01275 (2024).
[204] Guillermo Villate-Castillo et al. 2024. A systematic review of toxicity in large language models: Deinitions, datasets, detectors,
detoxiication methods and challenges. (2024).
ACM Comput. Surv.
34 • X. Mou et al.
[205] Boxuan Wang et al . 2024. Can LLMs Understand Social Norms in Autonomous Driving Games?. In Proc. IEEE Int. Automated Vehicle
Validation Conf. 1ś4.
[206] Chenxi Wang et al. 2024. Decoding echo chambers: Llm-powered simulations revealing polarization in social networks. arXiv:2409.19338
(2024).
[207] Chenxu Wang et al . 2024. Towards Objectively Benchmarking Social Intelligence for Language Agents at the Action Level. In Proc.
Annu. Meeting Assoc. Comput. Linguistics Finding. 8885ś8897.
[208] Guanzhi Wang et al. 2023. Voyager: An open-ended embodied agent with large language models. arXiv:2305.16291 (2023).
[209] Lei Wang et al. 2023. Plan-and-solve prompting: Improving zero-shot chain-of-thought reasoning by large language models.
arXiv:2305.04091 (2023).
[210] Lei Wang et al. 2023. Recagent: A novel simulation paradigm for recommender systems. arXiv:2306.02552 (2023).
[211] Lei Wang et al. 2024. A survey on large language model based autonomous agents. Frontiers of Computer Science (2024), 186345.
[212] Lei Wang et al . 2025. Investigating and Extending Homans’ Social Exchange Theory with Large Language Model based Agents.
arXiv:2502.12450 (2025).
[213] Lei Wang et al. 2025. Yulan-onesim: Towards the next generation of social simulator with large language models. arXiv:2505.07581
(2025).
[214] Pengda Wang et al . 2025. Personality Structured Interview for Large Language Model Simulation in Personality Research.
arXiv:2502.12109 (2025).
[215] Ruiyi Wang et al. 2024. SOTOPIA-pi: Interactive Learning of Socially Intelligent Language Agents. arXiv:2403.08715 (2024).
[216] Shenzhi Wang et al. 2023. Avalon’s game of thoughts: Battle against deception through recursive contemplation. arXiv:2310.01320
(2023).
[217] Xintao Wang et al. 2024. Incharacter: Evaluating personality idelity in role-playing agents through psychological interviews. In Proc.
Annu. Meeting Assoc. Comput. Linguistics. 1840ś1873.
[218] Xintao Wang et al. 2024. SurveyAgent: A Conversational System for Personalized and Eicient Research Survey. arXiv:2404.06364
(2024).
[219] Xintao Wang et al. 2025. CoSER: Coordinating LLM-Based Persona Simulation of Established Roles. arXiv:2502.09082 (2025).
[220] Yancheng Wang et al. 2024. RecMind: Large Language Model Powered Agent For Recommendation. In Proc. Conf. North Amer. Chapter
Assoc. Comput. Linguistics Finding. 4351ś4364.
[221] Zejun Wang et al. 2023. ChatCoder: Chat-based Reine Requirement Improves LLMs’ Code Generation. arXiv:2311.00272 (2023).
[222] Zhilin Wang et al. 2023. Humanoid agents: Platform for simulating human-like generative agents. arXiv:2310.05418 (2023).
[223] Zixiao Wang et al. 2025. Beyond Proile: From Surface-Level Facts to Deep Persona Simulation in LLMs. arXiv:2502.12988 (2025).
[224] Zekun Moore Wang et al. 2023. Rolellm: Benchmarking, eliciting, and enhancing role-playing abilities of large language models.
arXiv:2310.00746 (2023).
[225] Jason Wei et al. 2022. Chain-of-thought prompting elicits reasoning in large language models. Proc. Int. Conf. Neural Inf. Process. Syst.
35 (2022), 24824ś24837.
[226] Martin Weiss et al . 2024. Rethinking the Buyer’s Inspection Paradox in Information Markets with Language Agents. OpenReview
(2024).
[227] Yixuan Weng et al. 2024. Controllm: Crafting diverse personalities for language models. arXiv:2402.10151 (2024).
[228] R. Williams et al. 2023. Epidemic Modeling with Generative Agents. arXiv:2307.04986 (2023).
[229] Cheng-Kuang Wu et al. 2023. Large language models perform diagnostic reasoning. In Proc. Int. Conf. Learn. Representations Tiny
Papers.
[230] Dekun Wu et al . 2024. Deciphering digital detectives: Understanding llm behaviors and capabilities in multi-agent mystery games. In
Proc. Annu. Meeting Assoc. Comput. Linguistics Finding. 8225ś8291.
[231] Qingyun Wu et al. 2023. Autogen: Enabling next-gen llm applications via multi-agent conversation framework. arXiv:2308.08155
(2023).
[232] S. Wu et al. 2024. Enhance Reasoning for Large Language Models in the Game Werewolf. arXiv:2402.02330 (2024).
[233] Weiqi Wu et al. 2024. From Role-Play to Drama-Interaction: An LLM Solution. arXiv:2405.14231 (2024).
[234] Zhenyu Wu et al. 2023. Embodied task planning with large language models. arXiv:2307.01848 (2023).
[235] Zengqing Wu et al . 2024. Shall we team up: Exploring spontaneous cooperation of competing llm agents. In Proc. Conf. Empirical
Methods Natural Lang. Process. Finding. 5163ś5186.
[236] Zengqing Wu et al. 2025. LLM-Based Social Simulations Require a Boundary. arXiv:2506.19806 (2025).
[237] Zhiheng Xi et al. 2025. The rise and potential of large language model based agents: A survey. Science China Information Sciences 68, 2
(2025), 121101.
[238] Tian Xia et al. 2024. Measuring Bargaining Abilities of LLMs: A Benchmark and A Buyer-Enhancement Method. In Proc. Annu. Meeting
Assoc. Comput. Linguistics Finding. 3579ś3602.
ACM Comput. Surv.
From Individual to Society: A Survey on Social Simulation Driven by Large Language Model-based Agents • 35
[239] Jiannan Xiang et al. 2024. Language models meet world models: Embodied experiences enhance language models. Proc. Int. Conf.
Neural Inf. Process. Syst. 36 (2024).
[240] B. Xiao et al. 2023. Simulating Public Administration Crisis: A Novel Generative Agent-Based Simulation System to Lower Technology
Barriers in Social Science Research. arXiv:2311.06957 (2023).
[241] Chengxing Xie et al. 2024. Can Large Language Model Agents Simulate Human Trust Behaviors?. In Proc. Int. Conf. Learn. Represent.
Workshop.
[242] Qianqian Xie et al . 2023. The wall street neophyte: A zero-shot analysis of chatgpt over multimodal stock movement prediction
challenges. arXiv:2304.05351 (2023).
[243] Tianbao Xie et al. 2024. Openagents: An open platform for language agents in the wild. In Conf. Lang. Modeling.
[244] Zhifei Xie et al . 2024. DreamFactory: Pioneering Multi-Scene Long Video Generation with a Multi-Agent Framework. arXiv:2408.11788
(2024).
[245] Kai Xiong et al . 2023. Examining Inter-Consistency of Large Language Models Collaboration: An In-depth Analysis via Debate. In Proc.
Conf. Empirical Methods Natural Lang. Process. Finding. 7572ś7590.
[246] Congluo Xu et al . 2025. FinArena: A Human-Agent Collaboration Framework for Financial Market Analysis and Forecasting.
arXiv:2503.02692 (2025).
[247] Rui Xu et al . 2024. Character is Destiny: Can Large Language Models Simulate Persona-Driven Decisions in Role-Playing?
arXiv:2404.12138 (2024).
[248] Rui Xu et al. 2024. Mindecho: Role-playing language agents for key opinion leaders. arXiv:2407.05305 (2024).
[249] Y. Xu et al . 2023. Exploring Large Language Models for Communication Games: An Empirical Study on Werewolf. arXiv:2309.04658
(2023).
[250] Yisen Xu et al . 2025. MANTRA: Enhancing Automated Method-Level Refactoring with Contextual RAG and Multi-Agent LLM
Collaboration. arXiv:2503.14340 (2025).
[251] Zelai Xu et al . 2024. Language Agents with Reinforcement Learning for Strategic Play in the Werewolf Game. In Int. Conf. on Mach.
Learn.
[252] Jintang Xue et al . 2024. Bias and fairness in chatbots: An overview. APSIPA Transactions on Signal and Information Processing 13, 2
(2024).
[253] Zihan Yan et al. 2024. Social Life Simulation for Non-Cognitive Skills Learning. arXiv:2405.00273 (2024).
[254] Diyi Yang et al. 2024. Social skill training with large language models. arXiv:2404.04204 (2024).
[255] Hui Yang et al. 2023. Auto-gpt for online decision making: Benchmarks and additional opinions. arXiv:2306.02224 (2023).
[256] Ziyi Yang et al. 2024. OASIS: Open Agents Social Interaction Simulations on One Million Agents. arXiv:2411.11581 (2024).
[257] Shunyu Yao et al . 2024. Tree of thoughts: Deliberate problem solving with large language models. Proc. Int. Conf. Neural Inf. Process.
Syst. 36 (2024).
[258] Rong Ye et al. 2025. Multi-agent KTO: Reinforcing Strategic Interactions of Large Language Model in Language Game. arXiv:2501.14225
(2025).
[259] Jifan Yu et al. 2024. From MOOC to MAIC: Reshaping Online Teaching and Learning through LLM-driven Agents. arXiv:2409.03512
(2024).
[260] Xianhao Yu et al. 2024. MineLand: Simulating Large-Scale Multi-Agent Interactions with Limited Multimodal Senses and Physical
Needs. arXiv:2403.19267 (2024).
[261] Xiaoyan Yu et al. 2024. Neeko: Leveraging dynamic lora for eicient multi-character role-playing agent. arXiv:2402.13717 (2024).
[262] Yangbin Yu et al. 2024. Afordable Generative Agents. arXiv:2402.02053 (2024).
[263] Yeyong Yu et al. 2024. BEYOND DIALOGUE: A Proile-Dialogue Alignment Framework Towards General Role-Playing Language
Model. arXiv:2408.10903 (2024).
[264] Haoqi Yuan et al. 2023. Skill reinforcement learning and planning for open-world long-horizon tasks. arXiv:2303.16563 (2023).
[265] Xinfeng Yuan et al . 2024. Evaluating Character Understanding of Large Language Models via Character Proiling from Fictional Works.
arXiv:2404.12726 (2024).
[266] Murong Yue et al . 2024. MathVC: An LLM-Simulated Multi-Character Virtual Classroom for Mathematics Education. arXiv:2404.06711
(2024).
[267] Hanna Yukhymenko et al . 2024. A Synthetic Dataset for Personal Attribute Inference. In Proc. Int. Conf. Neural Inf. Process. Syst. D&B
Track.
[268] Qingbin Zeng et al. 2025. CrimeMind: Simulating Urban Crime with Multi-Modal LLM Agents. arXiv:2506.05981 (2025).
[269] Yongchao Zeng et al. 2025. Too Human to Model: The Uncanny Valley of LLMs in Social SimulationśWhen Generative Language
Agents Misalign with Modelling Principles. arXiv:2507.06310 (2025).
[270] A. Zhang et al. 2024. On Generative Agents in Recommendation. In Proc. 47th Int. ACM SIGIR Conf. Res. Dev. Inf. Retr. 1807ś1817.
[271] Ceyao Zhang et al . 2023. ProAgent: Building Proactive Cooperative Agents with Large Language Models. In AAAI Conf. Artif. Intell.
ACM Comput. Surv.
36 • X. Mou et al.
[272] Hongxin Zhang et al. 2024. Building Cooperative Embodied Agents Modularly with Large Language Models. In Proc. Int. Conf. Learn.
Representations.
[273] Jiayi Zhang et al. 2024. Alow: Automating agentic worklow generation. arXiv:2410.10762 (2024).
[274] Junjie Zhang et al . 2024. Agentcf: Collaborative learning with autonomous language agents for recommender systems. In Proc. World
Wide Web Conf. 3679ś3689.
[275] Jintian Zhang et al . 2024. Exploring Collaboration Mechanisms for LLM Agents: A Social Psychology View. In Proc. 62nd Annu. Meet.
Assoc. Comput. Linguistics, Vol. 1: Long Papers. 14544ś14607.
[276] Jizhi Zhang et al . 2024. Prospect Personalized Recommendation on Large Language Model-based Agent Platform. arXiv:2402.18240
(2024).
[277] Qiang Zhang et al. 2024. Self-Emotion Blended Dialogue Generation in Social Simulation Agents. In Proc. Annu. Meeting. Spec. Interest
Group Discourse Dialogue. 228ś247.
[278] Wenyuan Zhang et al . 2025. SOTOPIA-{\Omega}: Dynamic Strategy Injection Learning and Social Instruction Following Evaluation
for Social Agents. arXiv:2502.15538 (2025).
[279] Xinnong Zhang et al . 2024. ElectionSim: Massive Population Election Simulation Powered by Large Language Model Driven Agents.
arXiv:2410.20746 (2024).
[280] Xiaoqing Zhang et al. 2024. A Large-scale Time-aware Agents Simulation for Inluencer Selection in Digital Advertising Campaigns.
arXiv:2411.01143 (2024).
[281] Xinnong Zhang et al . 2025. Socioverse: A world model for social simulation powered by llm agents and a pool of 10 million real-world
users. arXiv:2504.10157 (2025).
[282] Yuntong Zhang et al. 2024. Autocoderover: Autonomous program improvement. In Proc. ACM SIGSOFT Int. Symp. Softw. Test. Anal.
1592ś1604.
[283] Yang Zhang et al. 2024. Towards Eicient LLM Grounding for Embodied Multi-Agent Collaboration. arXiv:2405.14314 (2024).
[284] Yiming Zhang, Pengcheng Li, and Xiaolong Wang. 2023. Multi-agent reinforcement learning meets agent-based modeling: A survey.
arXiv preprint arXiv:2303.13172 (2023). [new] Survey on combining MARL with ABM for social simulation.
[285] Qinlin Zhao et al. 2024. CompeteAI: Understanding the Competition Dynamics of Large Language Model-based Agents. In Proc. Int.
Conf. Mach. Learn.
[286] Hao Zheng et al. 2025. PPTAgent: Generating and Evaluating Presentations Beyond Text-to-Slides. arXiv:2501.03936 (2025).
[287] Yuhao Zheng et al. 2025. AutoCas: Autoregressive Cascade Predictor in Social Networks via Large Language Models. arXiv:2502.18040
(2025).
[288] Zhiling Zheng et al. 2023. Chatgpt research group for optimizing the crystallinity of mofs and cofs. ACS Central Science 9, 11 (2023),
2161ś2170.
[289] Jinfeng Zhou et al. 2024. CharacterGLM: Customizing Social Characters with Large Language Models. In Proc. Conf. Empirical Methods
Natural Lang. Process. 1457ś1476.
[290] Xuhui Zhou et al . 2024. Is this the real life? Is this just fantasy? The Misleading Success of Simulating Social Interactions With LLMs.
In Proc. Conf. Empirical Methods Natural Lang. Process. Finding. 21692ś21714.
[291] Xuhui Zhou et al. 2024. Sotopia: Interactive evaluation for social intelligence in language agents. In Proc. Int. Conf. Learn. Representations.
[292] Chen Zhu et al. 2024. Generative Organizational Behavior Simulation using Large Language Model based Autonomous Agents: A
Holacracy Perspective. arXiv:2408.11826 (2024).
[293] Jun-Peng Zhu et al. 2024. AutoTQA: Towards Autonomous Tabular Question Answering through Multi-Agent Large Language Models.
Proc. VLDB Endow. 17, 12 (2024), 3920ś3933.
[294] Qinglin Zhu et al. 2024. PLAYER*: Enhancing LLM-based Multi-Agent Communication and Interaction in Murder Mystery Games.
arXiv:2404.17662 (2024).
[295] Xizhou Zhu et al . 2023. Ghost in the minecraft: Generally capable agents for open-world environments via large language models with
text-based knowledge and memory. arXiv:2305.17144 (2023).
[296] Terry Yue Zhuo et al. 2023. On robustness of prompt-based semantic parsing with large pre-trained language model: An empirical
study on codex. arXiv:2301.12868 (2023).
[297] Andy Zou et al. 2023. Universal and transferable adversarial attacks on aligned language models. arXiv:2307.15043 (2023).
Received 22 April 2025; revised 7 February 2026; accepted 10 February 2026