# Related projects and design choices

Reviewed September 23, 2026. This is a comparison of documented workflows, not a security audit or performance benchmark. The projects remain independent; Twinquiry is not endorsed by them.

| Project | Form and useful idea | Twinquiry's choice |
| --- | --- | --- |
| [Claudex Loop](https://github.com/chaseai-yt/claudex-loop) | Skills plus a Python CLI adapter; cross-provider plan review, bounded loops, structured results | Explicit provider models, bounded review, validated result contracts; focus on research instead of implementation |
| [LLM Council](https://github.com/karpathy/llm-council) | Web application using OpenRouter; independent answers, anonymized peer ranking, chairman synthesis | Independent first answers and label-free candidate prompts; retain disagreement instead of assigning a chairman or winner |
| [codex-debate](https://github.com/octanevz/codex-debate) | Claude Code plugin/skill; iterative critique, blind initial positions, documented unresolved disputes | Cross-review with a round cap and retained unresolved findings |
| [MAGI Researchers](https://github.com/Axect/magi-researchers) | Claude Code plugin integrating multiple models and research artifacts across a larger pipeline | Explicit claim/evidence fields and saved artifacts; omit scientific execution, plotting and additional provider dependencies |
| [cross-review](https://github.com/xntj-ai/cross-review) | Claude Code skill with scripts; live research, role-specialized council and anonymized judgment | Optional fresh web evidence and a fixed review rubric; keep the initial runtime to two providers |

Twinquiry implements these general workflow patterns in its own small runtime. It does not vendor source files from the listed projects. Their licenses and notices must be checked and preserved if code is incorporated in future changes.

## Why not combine every feature?

A large council multiplies account setup, usage and failure points. Automatic fallback changes the experiment. A synthesized answer can conceal disagreements. Tool-heavy research can mix factual review with execution side effects.

The first release keeps a narrow contract: question, sources, two independent answers, cross-review, optional revision, and a traceable comparison report. Additional providers, a web interface, optional synthesis, and external benchmark scoring should be separate extensions backed by tests.

## Skill, plugin, or application?

A **skill** is an instruction package explaining how an assistant should do a task. A **plugin** distributes skills and sometimes executable tools or service connections. An **application/runtime** executes the workflow and records state itself.

Many cross-model repositories combine these forms. Claudex Loop contains skill instructions and executable orchestration helpers. LLM Council is an application. Twinquiry is currently a standalone CLI runtime: it can be driven from either assistant or a regular terminal, without relying on a particular assistant to remember the protocol.
