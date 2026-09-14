"""Recode rules for free-text answers.

Copied from the R rse-book, branch free-text-answers, commit b30d6bc. Each rule
maps a regex pattern to a category. A rule with category None excludes the
answer. The first matching rule wins. Questions without rules show their
answers unchanged.
"""

# ruff: noqa: E501  (the regex patterns are copied verbatim and stay on one line)

RECODE_MAPS: dict[str, list[tuple[str, str | None]]] = {
    "conf2can": [
        (
            r"(?i)\b(rse ?con|rsecon|de\s*rse|us[- ]?rse|nordic\s*rse|rsse|rse[- ]?day|rslondonsoutheast|rseaunz)\b",
            "RSE community conferences",
        ),
        (
            r"(?i)rse conferences|ukrse|rseconuk|nordicrsecon|gamms\s*rse|rse\s+chile|res? ?con\b",
            "RSE community conferences",
        ),
        (
            r"(?i)\b(sc|supercomputing)\b|\bisc\b(?!b)|\bpasc\b|pearc|cray user|\bchpc\b|techx|\bwlcg\b|openacc|durham hpc|globus(world)?|prace|ipdps|hpc days",
            "HPC and e-infrastructure",
        ),
        (
            r"(?i)egi\b|neic\b|hipeac\b|jlesc\b|google cloud summit|grid\b",
            "HPC and e-infrastructure",
        ),
        (
            r"ceci meeting|espresso summer school|cecam espresso summer school|adac",
            "HPC and e-infrastructure",
        ),
        (
            r"(?i)pycon|scipy|euroscipy|pydata|jupytercon|juliacon|python in heliophysics|pyhep",
            "Python/Julia/Jupyter ecosystem",
        ),
        (r"(?i)knime\b", "Python/Julia/Jupyter ecosystem"),
        (
            r"(?i)\buseR!\b|\buser!\b|posit::conf|rstudio::conf|latinr|rencontres\s*r",
            "R ecosystem",
        ),
        (r"(?i)user!|european r users meeting", "R ecosystem"),
        (
            r"(?i)\bdh\b(?!tech)|digital humanities|dh ?benelux|dhnb|eadh|caa\b|tei|tpdl|swib|elag|ests|archeofoss|språkbanken|theory and practice of digital libraries|text encoding",
            "Digital Humanities and GLAM",
        ),
        (
            r"(?i)dhtech symposium|including adho|huminfra nodes conference|european society for textual scholarship",
            "Digital Humanities and GLAM",
        ),
        (r"(?i)barcamp open science", "Digital Humanities and GLAM"),
        (
            r"african digital scholarship and curation|chr|dhd|digikult|musikwissenschaftliche themenkonferenz.*",
            "Digital Humanities and GLAM",
        ),
        (
            r"(?i)miccai|ismb|iscb|recomb\b|galaxy community|elixir|eccb|virus genomics|plant and animal genome|cancer genomics|ismrm|attd|one health|omics|sib\b|vibiom",
            "Bioinformatics and life sciences",
        ),
        (r"(?i)summer rosetta ?con", "Bioinformatics and life sciences"),
        (
            r"annual meeting of the american ornithological society|evolution and bioinformatics",
            "Bioinformatics and life sciences",
        ),
        (
            r"(?i)\baas\b|american astronomical|iau\b|cospar|spie(.*astronom)|\bastronom|space weather|heliophys|ivoa\b|lhcp|atlas|hep(?!a)|hepix|wlcg\b|lhc\b|aps(\s|$)|aiaa|magnetism|strong lensing|shine|higgs",
            "Astronomy, space and physics",
        ),
        (
            r"(?i)american physical society division of plasma physics annual meetings|acat\b|adass\b|adass and|icalepcs|pcapac|uklft|skach winter meeting|software defined space",
            "Astronomy, space and physics",
        ),
        (
            r"icns|inmm|iss|leipzig summer schoon on active matter|pac|spie",
            "Astronomy, space and physics",
        ),
        (
            r"(?i)\bagu\b|european geosciences union|\begu\b|goldschmidt|noaa.*space weather|ocean sciences|esa living planet|ewri|seismolog|\bssa\b|geophys|meteorolog|\bams\b(?![a-z])",
            "Geosciences and environment",
        ),
        (
            r"(?i)california forestry science symposium|ecological modelling conference|north american forestry ecology workshop|igarss\b|nerc digital gathering|liege colloquium",
            "Geosciences and environment",
        ),
        (
            r"ciroh developers conference|monogram|programación en ciencias pesqueras|south african society of atmospheric scientists",
            "Geosciences and environment",
        ),
        (
            r"(?i)\bsiam\b|compstat|cmstatistics|\bjsm\b|\bgamm\b|euromech|icosahom|lattice conference|\bwccm\b|\becm\b|siam (cse|pp)",
            "Mathematics and statistics",
        ),
        (
            r"(?i)biometrisches kolloquium|australasian region biometrics conference|rss\b|uk fluids",
            "Mathematics and statistics",
        ),
        (
            r"(?i)\bacl\b|emnlp|coling|cvpr|vision sciences society|\bai\b|machine learning",
            "AI, NLP and vision",
        ),
        (
            r"(?i)empirical methods in natural language processing conference|lrec\b|swedish language technology conference|dlr llm wissensaustauschworkshop",
            "AI, NLP and vision",
        ),
        (
            r"(?i)\bacs\b|iucr\b|epdic|emrs|synchrotron|\bsri\b|nobugs|crystallograph|diffraction|watoc",
            "Chemistry, materials and photon science",
        ),
        (
            r"(?i)american chemical society|faraday discussions|siesta advanced workshop|mse\b",
            "Chemistry, materials and photon science",
        ),
        (r"(?i)sers\b", "Chemistry, materials and photon science"),
        (
            r"(?i)\bicse\b|icsew|pepm|doceng|chase|wssspe|ssp(\s|\()|fosdem|declarative amsterdam|open source software for fusion|ieee e?science|eresearch|tnc\b|cni\b",
            "Software engineering and e-Science",
        ),
        (
            r"(?i)escience|chaos communication congress|gitkon|tiime\b|knime\b|google cloud summit|hpsf conference|u?car sea'?s improving scientific software",
            "Software engineering and e-Science",
        ),
        (
            r"acts developer workshop|aviose|cakefest|forge",
            "Software engineering and e-Science",
        ),
        (r".*(ssp)", "Software engineering and e-Science"),
        (
            r"(?i)sunbelt|insna|\beusn\b|netsci|\bwapor\b|vision sciences society",
            "Social sciences and networks",
        ),
        (
            r"(?i)aoir\b|oecd\b|ifd&tc|afrilex|comparative.*linguistics|issi\b|issb\b",
            "Social sciences and networks",
        ),
        (
            r"land warfare conference|military information and communications symposium.*",
            "Social sciences and networks",
        ),
        (
            r"(?i)\bsfn\b|society for neuroscience|ocns annual|interamerican congress of psychology|caribbean regional conference of psychology",
            "Neuroscience and psychology",
        ),
        (r"(?i)ebrains ?/ ?hbp summit|practicalmeeg", "Neuroscience and psychology"),
        (
            r"(?i)metadata|\bhmc\b|mpg fdm|fdm workshop|nfdi|saxfdm",
            "Research data management and metadata",
        ),
        (
            r"(?i)eln workshops|educause|worktribe connect",
            "Research data management and metadata",
        ),
        (r"acm document engineering|dash", "Research data management and metadata"),
        (
            r"(?i)domain (conferences|workshops)|project (workshops|specific conference)|other consortium|community workshops|mostly community|workshops hosted|workshops within|internal (workshops|wissensaustausch)|university|open science days|collegeville|collaborations workshop",
            "Domain/project/internal workshops",
        ),
        (
            r"(?i)interne wissensaustausch workshop|interne workshops|topical conferences|user meetings|eln workshops",
            "Domain/project/internal workshops",
        ),
        (
            r"(?i)multiple|varies|very different|a few|many|not software conferences|where our users go to|other online formats|canberra|england|stockholm|sweden|gdansk",
            "Multiple or unspecified conferences",
        ),
        (
            r"(?i)research area specific not software specific conferences|diverses conférences|gordon research conference",
            "Multiple or unspecified conferences",
        ),
    ],
    "currentEmp13": [
        (
            r"(?i)digital\s*humanit|\bdh\b|digital humanitit|library|information\s+science\b|informationswissenschaft|bibliotec|bilbiotecas y apoyo a la investigación",
            "Digital humanities and LIS",
        ),
        (
            r"(?i)environment|ecolog|earth|\beath\b|geolog|geochem|geoscien|geowissenschaft|geographie|\bgeography\b|geoinformat|meteorolog|climate\s*science",
            "Earth and environmental sciences",
        ),
        (
            r"(?i)astro|cosmo|particle\s*physics|solar\s*system|planetary|nuclear\s*physics|space\b",
            "Physics and space sciences",
        ),
        (
            r"(?i)\bchem|chemical\s*sciences|electro\s*chem|material\s*science",
            "Chemistry and materials",
        ),
        (r"(?i)bioinform|neurosci|neurowissenschaft", "Life sciences and neuroscience"),
        (
            r"(?i)aerospace|robotics|high\s*performance\s*computing|\bhpc\b|software\s*development|infrastructure|security\b|fintech|information\s*systems|data\s*visuali|\brse\b|research\s*data\s*management|\bstatistics\b",
            "Computing, data and engineering",
        ),
        (
            r"(?i)\bhumanities\b|geisteswissenschaft|kunstwissenschaft|literature|geschichts|justice\b|sciences\s+de\s+l'?orientation|social\s*sciences",
            "Humanities and social sciences",
        ),
        (
            r"(?i)any\s*really|so\s*all\s*of\s*the\s*above|research\s*agnostic|operate\s*university|depends\s*on\s*who\s*asks|general\s*consulting|anwender\s*sind\s*aus\s*allen\s*möglichen\s*gebieten|natural\s*sciences\b|we\s*operate\s*university",
            "Cross-cutting / research-wide",
        ),
        (r"archaeology", "Archaeology"),
    ],
    "currentWork2qcl": [
        (
            r"(?i)instituci(ó|o)nes|\binstitution(s)?\b",
            "External institutional partners",
        ),
        (r"(?i)project[- ]based", "Project-based collaborators"),
        (
            r"(?i)within the university|\bdepartment\b",
            "Within institution (dept/university)",
        ),
        (
            r"(?i)\bfield of research\b|\bmy field\b|researchers in our field",
            "Field-specific researchers",
        ),
        (r"(?i)business automation", "Business process automation"),
        (
            r"(?i)global(ly)?\)?|worldwide|international(ly)?|anywhere|no matter which country|forschende international|researchers around the world|researchers worldwide|global research area",
            "Global/international researchers",
        ),
        (
            r"(?i)in principle anyone|anyone who wants to use|regardless of affiliation|international projects|maintained public services",
            "Global/international researchers",
        ),
    ],
    "fund3": [
        (r"(?i)\b(european project|eu(rope)?)(s)?\b", "Public grants and programmes"),
        (r"(?i)\b(federal funding|national funding)\b", "Public grants and programmes"),
        (
            r"(?i)\b(private philanthropy|philanthropy)\b",
            "Private/philanthropic support",
        ),
        (r"(?i)\b(service contracts?)\b", "Earned/contract income"),
        (r"(?i)\b(subscriptions?)\b", "Earned/contract income"),
        (
            r"(?i)\b(self[- ]employment|self employment|freelance|consult(ing|ancy))\b",
            "Earned/contract income",
        ),
        (
            r"(?i)\b(institutional|core funding).*\b|\bsupposed to become institutional over the next years\b",
            "Institutional/core funding",
        ),
    ],
    "fund3qnl": [
        (
            r"(?i)all of the above|\berc and horizon\b|nwo\s*\+\s*groeifonds",
            "Multiple grants",
        ),
        (
            r"(?i)open\s*science\s*(nl|council)|nwo\s*/\s*open\s*science\s*council",
            "Open Science NL / Council",
        ),
        (r"(?i)horizon\s*europe(n)?\b", "Horizon Europe"),
        (r"(?i)\berc\b", "ERC"),
        (r"(?i)\bzon\s*mw\b|\bzonmw\b", "ZonMw"),
        (r"(?i)\bnwo\b|\bvidi\b", "NWO"),
        (r"(?i)\bukri\b", "UKRI"),
        (r"(?i)^eu$", "EU (unspecified)"),
        (r"(?i)internal\s+university\s+grant", "Internal university grant"),
        (r"(?i)^thematic(\s+dcc)?$", "Thematic"),
        (r"(?i)\blsri\b", "LSRI"),
        (r"(?i)bioimaging", "Bioimaging"),
    ],
    "genAI2": [
        (
            r"(?i)pros and cons|trade[- ]?off|second opinion|abw(ä|a)gen|choices",
            "Evaluation and decision support",
        ),
        (
            r"(?i)\bpo[cf]\b|proof of concept|scaffold|template(s)?\b|code outline|outline(s)?\b|dockerfile|pattern implementation|prototyp|writing parsers",
            "Prototyping and scaffolding",
        ),
        (
            r"(?i)understanding( ill-documented)? code|make? ?ing sense of code|navigate.*code ?bases?|responsive rubber duck(y)?|rubber duck|problem solving|verstehen von code|prompting for a solution of a task that does not seem to have a straightforward answer on forums",
            "Code comprehension and problem solving",
        ),
        (
            r"(?i)checking syntax|get(ting)? (information )?about syntax|get(ting)? help with (libraries|library|api)|which libraries exist|question on how to use a library|refactor(ing)?|formatting|naming variables|tooling|testing crazy ideas.*",
            "Code assistance and refactoring",
        ),
        (
            r"(?i)code review(s)?|review(ing)? (my )?code|linting",
            "Code review and linting",
        ),
        (
            r"(?i)documentations|documenting existing codebases|entry points? to documentation|learn(ing)? (new|unknown)? (software )?technolog|finding resources|domain knowledge",
            "Documentation",
        ),
        (r"understanding ill-documented legacy code", "Documentation"),
        (
            r"(?i)brainstorm|conceptualis(e|ing)|planning|getting ideas|exploratory prigramming",
            "Brainstorming and planning",
        ),
        (
            r"(?i)improv(ing|e) (the )?wording|spelling/grammar|grammar checking|summari(s|z)e|check my own writing|writing (documents|non-technical overviews)|emails?|blog posts|turning my .*infodumps|general non-technical communication|making images? for presentations",
            "Writing (grammar/spelling) and communication",
        ),
        (
            r"(?i)data extraction|datenanreicherung|natural language processing|text classification|sentiment analysis|plotting of data",
            "Data and analysis tasks",
        ),
        (r"papers", "Papers"),
        (
            r"learn how to apply new or unknown technologies|ask(ing)? questions of rag|\brag[- ]?based|research on technical solutions|to get the domain knowledge that i need for the current projects|double check techniques.*|where i can learn the details error free|best practices",
            "Learning",
        ),
        (r"specially when it's a technology i'm not very familiar with.|etc.", None),
        (
            r"(?i)ai is rarely good enough|mostly checking if llms can be helpful|^etc\.?$|have a laugh|launching pad",
            None,
        ),
    ],
    "genAI3": [
        (
            r"(?i)\bmistral(\s*vibe)?\b|\ble\s*chat\b|\bmistral(ai)?\s*le\s*chat\b",
            "Mistral (Le Chat, Vibe)",
        ),
        (r"(?i)\bperplexity(\.ai)?\b", "Perplexity"),
        (r"(?i)\bdeep\s*seek\b", "DeepSeek"),
        (
            r"(?i)\bqwen\b|\bqwen\s*3\b|\bqwen3\b|qwen-?coder|qwen3-?next|qwen3 coder|qwent 3 coder|locally hosted qwen",
            "Qwen family",
        ),
        (r"(?i)\bclaude(\s*code)?\b", "Claude"),
        (r"(?i)\bgrok\b", "Grok"),
        (r"(?i)\bphind\b", "Phind"),
        (r"(?i)\bjetbrains\s*ai\b", "JetBrains AI"),
        (r"(?i)\bsupermaven\b", "Supermaven"),
        (r"(?i)\bwind\s*surf\b", "Windsurf"),
        (r"(?i)\bcodex\b|openai\s*codex", "OpenAI Codex"),
        (
            r"(?i)\bmicrosoft\s*co-?pilot\b|\bms\s*copilot\b|\bcopilot\b",
            "Microsoft/GitHub Copilot",
        ),
        (r"(?i)\bmistral\b", "Mistral (Le Chat, Vibe)"),
        (r"(?i)helmholtz\s*blablador|\bblablador\b", "Helmholtz Blablador"),
        (
            r"(?i)gwdg\s*chat-?ai|academiccloud|chat-?ai\.?academiccloud\.de|chat-?ai\s*gwdg",
            "GWDG / AcademicCloud Chat-AI",
        ),
        (r"chatai", "GWDG / AcademicCloud Chat-AI"),
        (
            r"(?i)inference-?as-?a-?service.*(epfl|rcp)|rcp\s*@\s*epfl",
            "EPFL RCP inference service",
        ),
        (
            r"(?i)(self[-\s]?hosted|self\s* hosted)|\bon-?prem\b|\bvllm\b|\bin-?house\b|\bin house\b|\binternal(ly)?\b|company\s*ai|gpt\s*uio|firmeninterne agents",
            "Institution-hosted LLMs",
        ),
        (
            r"\blocal(ly)?(-|\s)?(hosted|deployed)?\b|local openai instance|we run local models",
            "Local LLMs",
        ),
        (r"(?i)\bollama\b", "Ollama"),
        (
            r"(?i)open\s*(source|weights)\s*models|gpt-oss",
            "Open-source/open-weights models",
        ),
        (r"(?i)\bproton\s*lumo\b|\blumo\b", "Proton Lumo"),
        (r"(?i)duck\s*ai|duckduckgo", "DuckDuckGo AI"),
        (r"(?i)open\s*code\b|\bopencode\b", "OpenCode platform"),
        (r"(?i)\bkimi\b|kimi-?k2", "Kimi"),
        (r"(?i)serena", "Serena"),
        (r"(?i)antigravity", "Antigravity"),
        (r"(?i)ide\s*integrated\s*ai\s*tools|continue", "IDE-integrated AI"),
        (r"(?i)^e\.g\.$", None),
        (r"e.g.", None),
    ],
    "skill2": [
        (
            r"(?i)\b(ai[- ]assisted|ai[- ]enhanced|llm[- ]assisted|coding agents?|agent(ic)? (ai|coding|loops)|ai tools?|gen( )?ai|mcp|model context protocol|prompt(ing)? ai|use of ai( tools)?|usage of ai|ai usage|using ai\b|using llms? and agents|integrat(e|ion) of ai|harness(ing)? ai|leverage(ing)? ai|proper use of llm|local llm|via llama\.cpp|coding with ai|ai agent(s)?|ai assistants|effective ai use|utili[sz]ation de l.*intelligence artificielle|utiliation de l'?ia|c[oó]mo usar .* ia|utilizing ai agents|ai in rse proficiency|ai‑enhanced software engineering|llm agent (management|orchestration)|ki als hilfe)|coding in cooperation with coding assistants",
            "AI-assisted development and agents",
        ),
        (
            r"(?i)ai development|\bai\b|vibe coding|but with human oversight.*",
            "AI-assisted development and agents",
        ),
        (
            r"(?i)\b(ml/ai|ai ?& ?ml|ai and ml|ai/ml|machine learning(?!.*assist)|deep learning|neural (nets?|networks)|statistical learning|transformer|diffusion|pytorch|jax|reinforcement learning|how to train large neural networks|ml algorithms?|ml/ops|llm(?!.*assist)|llm and ml development|language technology|nlp\b)\b",
            "AI/ML theory and model development",
        ),
        (
            r"(?i)\bml\b|algorithm assessment|e\.g\. anomaly detection",
            "AI/ML theory and model development",
        ),
        (
            r"(?i)\b(hpc|high[- ]performance( and parallel)? computing|parallel( programming|i[sz]ation| processing| management)?|cuda|openacc|openmp|mpi|slurm|gpu( computing| programming| offload| processing| support|-based| acceleration)?|tpu|bare[- ]metal gpu|multi gpu|multi cpu|vectori[sz]ation|ray\b|dask\b|numba\b|cupy\b|driver level understanding of hpc|cluster management|pipeline with hpc|learning .*accelerators such as gpus/tpus|using gpus)\b",
            "HPC, parallel and GPU computing",
        ),
        (
            r"(?i)paralellization \(in-depth\)|parallized hardware",
            "HPC, parallel and GPU computing",
        ),
        (
            r"(?i)\brust\b|rust (fluency|proficiency|programming|development|integration with python|hpc with rust|embedded with rust)",
            "Programming language: Rust",
        ),
        (
            r"(?i)(\bc\+\+|advanced c\+\+|c\+\+\s*23|always improving c\+\+ skills|improve c\+\+|c\+\+ language|c\+\+ programming|deeper understanding of julia and c\+\+)|\badvanced c programming\b|\blow[- ]level programming in c/c\+\+\b",
            "Programming language: C/C++",
        ),
        (
            r"(?i)\bpython\b|advanced python|better at python|improve on python|python best practices|python ecosystem|fastapi|pandas|geopandas|django\b|mypyc\b",
            "Programming language: Python",
        ),
        (
            r"(?i)generating code using symbolic tools \(sympy\)",
            "Programming language: Python",
        ),
        (r"(?i)\bjulia\b|documenter\.jl", "Programming language: Julia"),
        (
            r"(?i)\bR\b(?!SE)|\bshiny\b|visualisation with r|cran compliance|programming shiny",
            "Programming language: R",
        ),
        (
            r"(?i)\b(go|golang)\b|learning go / web assembly|web ?assembly|wasm\b|learning rust / zig|zig\b|\bassembly\b",
            "Programming language: Go/Zig/WASM/Assembly",
        ),
        (
            r"(?i)javascript|modern javascript|advanced javascript|typescript|angular\b|react\b|java\b|dart\b",
            "Programming language: JS/TS/Java",
        ),
        (
            '(?i)\\bsql\\b|database(s)?|postgres|mongodb|proper sql course|using a "real" database|base de datos|base de donn(?:é|e)es|knowledge of databases|i would like to understand databases better|xquery\\b',
            "Data storage and databases",
        ),
        (
            r"(?i)\b(devops|ci/?cd|\bci\b|\bcd\b|continuous (integration|deployment)|pipelines?|github actions|gitlab( ci)?/ci/cd|helm|ansible|orchestration\b|the ops part of devops|advanced ci/cd|gitlab-ci|caching effectively|deployment(?!.*/)|software deployment|operations\b|webhooks?)\b",
            "DevOps, CI/CD and pipelines",
        ),
        (r"(?i)reliability engineering", "DevOps, CI/CD and pipelines"),
        (
            r"(?i)\b(container(isation|ization|s?)|docker|kubernetes|k8s|cloud( computing| infrastructure| native|/?high performance computing)?|aws|amazon web services|azure|gcp|okd\b|scaling cloud|cloud/distributed systems|cloud-related skills|leveraging cloud resources|resource allocation on cloud|arquitectura serverless|contenedores docker|distributed (computing|systems)|compute resource management)\b",
            "Cloud, containers and Kubernetes",
        ),
        (
            r"(?i)\b(git\b|version control|version management|branches|pre-commit|github(?! actions)|gitlab\b|use of git|better routine in version control|uso github)\b",
            "Version control (Git) and collaboration",
        ),
        (r"(?i)collaborating", "Version control (Git) and collaboration"),
        (
            r"(?i)^(architecture)$|\b(software (architecture|architektur|achitecture|achitecture patterns)|systems? (architecture|design)|system-engineering|system design|architecture (design|documentation|and road mapping|road ?mapping|& road mapping)|enterprise architecture|deepen .* software architecture|planen der sw architektur|architektur|aquitectura de software|softwarearchitekturgestaltung|noch mehr über softwarearchitektur lernen)\b",
            "Software architecture and system design",
        ),
        (
            r"(?i)code base structures|scalability\)|socio-technical systems thinking|learn more about structuring|formale softwarearchitektur für objektorientierte sprachen",
            "Software architecture and system design",
        ),
        (
            r"(?i)\b(requirements( engineering| analysis| elicitation)?|analisis de requerimientos|requirement engineering( methology)?)\b",
            "Requirements engineering and analysis",
        ),
        (
            r"(?i)\b(software design( and architecture)?|software design process|software design patterns|object[- ]oriented (programming|scientific software design)|design patterns( for .*|)|codebase design|clean code|clean coding|good practices? in software development|best practices(?!.*testing)|proper design instead of patching holes|aprender .* diseñar código a nivel avanzado|bonnes pratiques de conception|reusable patterns)\b",
            "Software design principles and patterns",
        ),
        (
            r"(?i)choosing the right pattern the first time around|matching code complexity .*|modular(ity)?|naming and structuring files and directories",
            "Software design principles and patterns",
        ),
        (
            r"(?i)\b(mathematics|linear algebra|h[öo]here mathematik|fortgeschrittene algebra und analysis|foundational maths? and computer science|general computer science knowledge|more basics of computer science|formal algorithmic and data structure education|data structure(s)? and algorithms?|statistics\b|statistical theory|foundational programming|theory)\b|data analysis|data science",
            "Mathematics/Statistics/Computer Science",
        ),
        (
            r"(?i)^(software development)$|^(coding)$|\b(professional software development|software development lifecycle|modern collaborative software practices|nuevas metodolog(i|í)as de desarrollo|experience with professional code production|using development methodologies in academic environment|software development - in the sense of professional technique|up to industry standards|software engineering skills|software development tools|software development with a team|software development/management models|core coding|coding expert|general coding skills|just improve my coding knowledge|functional programming|asynchronous programming|learning new programming languages|second programming language|better programming)\b",
            "Software development practices and SDLC",
        ),
        (
            r"(?i)better coding knowledge\.|but more techniques should help|e\.g\. in a software company|fast prototyping|methods|technical coding skills|better understanding of how to do things.*|bonnes pratiques de maintenance|me gustaría mejorar mi conocimiento sobre.*",
            "Software development practices and SDLC",
        ),
        (
            r"(?i)\b(test(ing)?(?!.*data)|unit tests?|tdd|test[- ]driven|mock(ing)? frameworks?|qa|quality control|formal testing|verification|validation|ci.*testing|automated testing|automatic testing|test harness(es)?|extended software testing|testing strategies|gute tests|testing tools and methodologies|understand how to really write tests|systematischeres testen|software quality assessment|separating e?vironments and running tests with big data|automatisiertes testen|formale begriffe des softwaretestings)\b",
            "Software testing, QA and verification",
        ),
        (r"(?i)debuging|formale methoden", "Software testing, QA and verification"),
        (
            r"(?i)\b(documentation|documenting\b|docstrings|readme|documentation generation|documentation maintenance|documentation management|documentation writing|developing code documentation|effektive dokumentation|better documentation skills|more time for writing proper documentation|research device documentation|latex|tikz)\b",
            "Software Documentation",
        ),
        (
            r"(?i)developing content for longer courses versus one-shot tutorials|generación de contenido|rse vocabulary|organising courses .*",
            "Software Documentation",
        ),
        (
            r"(?i)\b(profil(e|ing)|optim(iz|is)e|optimization|optimierung|performance( engineering| testing)?|benchmark(ing)?|vectori[sz]ation|code optimisation|runtime optimization|ptx/gfx analysis|deeper knowledge of performance optimizations|profiling code both cpu and gpu|producing an efficient code|scaling up applications to be production ready)\b",
            "Performance engineering and optimisation",
        ),
        (r"(?i)efficient\b", "Performance engineering and optimisation"),
        (
            r"(?i)\b(security|cyber(security)?|network security|secure coding|pentest|airworthiness certification|höheres maß an sicherheit|application security|web development security principles|security skills for mobile applications)\b",
            "Security and secure engineering",
        ),
        (
            r"(?i)\b(web( dev| development| framework| app| backend| frontend|[- ]based application)|front[- ]?end development|back[- ]?end development|backend development|full[- ]stack development|ui/?ux|ux/?ui|user (experience|interface design|profiling|management and interaction)|interface(s)? graphiques|web ui|css|working with user interface toolkits|ui design|ux design|\(web\) ui creation and design|ux( /|/)? ?ui design|ux/?ui research|\bmobile (app|application)s?\b|ios\b|android\b|gui development|interface design)\b",
            "Web development, UI and UX",
        ),
        (
            r"(?i)ux research|.*creation and design|full stack management|localization",
            "Web development, UI and UX",
        ),
        (
            r"(?i)\b(data (engineering|management|storage|sharing))\b",
            "Data engineering/management and FAIR",
        ),
        (
            r"(?i)analytics|data visualization|interoperability|estadistica|systems engineering|data fair and metadata standards",
            "Data engineering/management and FAIR",
        ),
        (
            r"(?i)\b(project (management|planning|manangement|managing|organisation|leadership|publishing|resilience)|product management|portfolio management|roadmaps?|milestones?|technical project management|project/time management|project management/ roadmaps/ milestone setting|research (software )?project management|softwareprojektmanagement|projektmanagement|gesti[oó]n de proyectos|gestion de projets|methodology for agile multiproject management|scrum/agile|agile management|agile methoden|risk management|issue triage and management|handling large-scale projects|managing large software projects|managing many projects|more formal ways to assess the resources needed|better planning .* required for a project|ressourcenmanagement|planning/scoping research software projects)\b",
            "Project/product/time management",
        ),
        (
            r"(?i)traveling skills|time & workload estimation|learn how to properly organize of bigger projects|change management|accounting|costs of work.*|estimation\b|planning$|planning/organisation|\bproject$|thinking about the bigger picture / next step in the project",
            "Project/product/time management",
        ),
        (
            r"(?i)^(management)$|\b(lead(ership)?|team (lead(ing|ership)?|management)|manag(e|ing) a team|stakeholder (management|communication|product ownership)|supervision of junior rses|mentoring(?!.*tools)|mentoring junior developers|mentoring more junior colleagues|rse leadership management|coordinating teams of rses|group management|people management|laterales f[üu]hren|leader skills|management skills\b|management/delegation|delegation\b|how to deal with people who aren't team players|how delegate tasks\)?)\b",
            "People leadership and stakeholder management",
        ),
        (
            r"(?i)coaching|better / more efficient communicaton skills|better management of people's expectations|how to build an internal rse organization\.|how to convince management to invest in paying down technical debt\.|relationship management|running meetings well|staff management\)|strategy\b|metodolog[ií]as para coordinar equipos de trabajo .*|teamleading|gaining more experience with leading a group",
            "People leadership and stakeholder management",
        ),
        (
            r"(?i)\b(communication|communicat(e|ing)|presentation|presenting|teaching|pedagogy|didactic|story telling|scientific communication|technical writing|professional writing|report writing|writing (skills|papers|software papers)|academic writing|research writing|presenting/teaching|create more effective learning content|being more effective with outreach|outreach|talking about what i do|talking with non technical pis|better academic skills in regards to publishing papers|mejorar en la comunicaci[oó]n y planificaci[oó]n|kommunikationsf[aä]higkeiten|training graduate or undergraduate students)\b",
            "Communication, teaching and writing",
        ),
        (
            r"(?i)knowledge transfer of software paradigms|organising courses .*|how to teach effectively\?|to be a better teacher|long-form writing|asking the right questions",
            "Communication, teaching and writing",
        ),
        (
            r"(?i)\b(grant( |-)?(writing|proposal|application|applications?)|fund(ing|raise|raising)|nsf\b|nasa\b|broadening funding base|consult(ing|ancy)|sales( & marketing)?|marketing|promote my (projects|work)|acquiring new projects|grant/application writing|publicizing and promoting my software|find a longterm contract|how to find people who value my skills and want to offer me a job|gesch[aä]ftst[üu]chtigkeit|gr[üu]ndermentalit[aä]t|business management|contract negotiations|negotiation|negotiating|writing successful grant proposals)\b",
            "Grants, funding, consultancy and marketing",
        ),
        (
            r"(?i)sell yourself better|how to sell infrastructure work|difusi[oó]n de productos|reaching / engaging users|improving institutional-level appreciation of rse work",
            "Grants, funding, consultancy and marketing",
        ),
        (
            r"(?i)\b(workflow(s)?( management)?|snakemake\b|automation\b|automated\b|dirk\b|jube\b|streamlined workflow development|efficiently managing research software projects|formal use of project managment software|learn to use a workflow management tool|efficiently using the gui|task management)\b",
            "Workflow management and automation",
        ),
        (
            r"(?i)\b(packag(e|ing)|software distribu(tion|ion)|cross platform packaging|guides for packaging python with conda|decisiones a la hora de crear paquetes|using virtual environments|proper db management)\b",
            "Packaging and software distribution",
        ),
        (
            r"(?i)\b(sustainab(le|ility)|maintainab(le|ility)|software maintenance|research software maintenance|reproducib(le|ility)|open-?source|licen[cs]es?|ip\b|intellectual property|software carpentry|software sustainability|fair expertise|making software fair and reproducible|reproducibilidad y sostenibilidad del software|licenciamiento y atribuci[oó]n|research software management|research software dissemination)\b",
            "Research software sustainability and open source",
        ),
        (
            r"(?i)open source hardware",
            "Research software sustainability and open source",
        ),
        (
            r"(?i)\b(linux\b|system administration|kernel|driver|low[- ]level (linux|cpu|programming|computing)|lower[- ]level programming|operating systems|os details|embedded\b|fpga\b|vhdl\b|verilog\b|computer architecture|hardware accelerated computing|high-level synthesis for fpgas|formal verification for fpgas|systems-level development|server configuration|how to set up a server|infrastructure/cluster development|ros\b|more on the configuration of local servers/clsuters|more on the configuration of local servers/clusters)\b",
            "Systems, OS, embedded and hardware/FPGA",
        ),
        (
            r"(?i)deeper knowledge of underlying infrastructure|reverse engineering von proprietären dateiformaten|more hardware knowledge|better understanding of hardware",
            "Systems, OS, embedded and hardware/FPGA",
        ),
        (
            r"(?i)\b(network (engineering|security)|observability|monitoring|metrics|grafana)\b",
            "Networking, observability and monitoring",
        ),
        (
            r"(?i)\b(collaboration|collaborative (coding|software development)|community( building| management| organizing)?|communities of practice|networking(?! (engineering|security))\b|seeking collaborations|recruiting contributors|team- und communitybuilding|kollaborations-modelle|partner\(s\) for code reviews|most of my projects are solo and i find combining efforts|überblick .* fachcommunity|colaboraci[oó]n efectiva|closer contact to scientists and scientific methods|participatory (co-production) approaches)\b",
            "Collaboration and community building",
        ),
        (
            r"(?i)accessibility and inclusivity|code review|hackathon management|building code all alone|especially within collaborations\)|navigating the politics of science collaborations|since all the positions i curently see are hiring .*",
            "Collaboration and community building",
        ),
        (
            '(?i)\\b(refactor(ing)?|improve ability to refactor|legacy code|code sustainability|code future-proofing|readability of code|clean code in long term project|proper software engineering|better understanding of how to do things "properly"|debug(ging)?)\\b',
            "Refactoring and code quality",
        ),
        (r"(?i)and navigable code\.", "Refactoring and code quality"),
        (
            r"(?i)\b(soft skills|confidence|self-accountability|saying no|empathy|social( skills|ising)|working with difficult personalities|better (organisation|organization) and time prioritisation|time management|gtd\b|organise myself better|better estimate of how long work will take|better prioritisation skills|stress management|having more time|know how to free time slots|remembering people's name|thinking outside the box)\b",
            "Personal stress/time/task management",
        ),
        (
            r"(?i)expectation management|managing my time across many projects|more time for practice|creative problem solving",
            "Personal stress/time/task management",
        ),
        (
            r"(?i)\b(physics|chemistry|structural biology|atmospheric science|computational biology|genomic data|differential equations|numerical computing|process modeling and mining|signal processing|simulations?|cosmo( transitions)?|synchrotron|airworthiness|simulaton based inference|causality analysis|image and video processing|computational minimization techniques)\b",
            "Domain-specific scientific knowledge",
        ),
        (
            r"(?i)research skills|research skills required|\bresearch\b|binary fission|better domain knowledge on long-term projects",
            "Domain-specific scientific knowledge",
        ),
        (
            r"(?i)\b(ides?|language server protocol|github prof+ecienc(y|e))\b",
            "Developer tooling",
        ),
        (r"(?i)analysis tooling\+\+.*|new tools", "Developer tooling"),
        (
            '(?i)\\b(how to go from "code in jupyter notebook" to an "interactiave app"|browser-based visualisations|python packages for webapp backend development|despliegue de modelos .* entornos web)\\b',
            "From notebooks to apps and productization",
        ),
        (r"(?i)law|legal aspects|legal knowledge|cross border dta", "Legal Knowledge"),
        (
            r"(?i)specific languages|new programming language|learn object orientation\?|expanding to other languages|better matlab|additional language with object oriented environment|\bstan\b|structured way of improving my coding knowledge|3d game engine programming|differentiable programming|improve knowledge of my main programming language",
            "New programming language (generic)",
        ),
        (
            r"i dont know|idk|none|telepathy|adjust chair for comfortable sitting|and the primary maintainer treats it like a personal fief and resists basic things like branch protection for main|to gain experience|participatory (co-production) approaches to rs development|trainings|more infra mainly|i am occasional developer\.",
            None,
        ),
        (r"(?i)^(etc\.?\)?|e\.g\.?)$", None),
        (r"(?i)^programming$", None),
        (r"(?i)^\.\.\.\)?$", None),
    ],
    "tool4can": [
        (
            r"(?i)wolfram\s*language|wolfram\s*/?\s*mathematica|^wolfram\b|^mathematica$",
            "Wolfram Language (Mathematica)",
        ),
        (r"(?i)idl\b|pv\s*-?\s*wave|pvwave", "IDL/PV-WAVE"),
        (r"(?i)xquery|\bxql\b", "XQuery/XQL"),
        (r"(?i)^xslt$", "XSLT"),
        (r"(?i)^sparql$", "SPARQL"),
        (r"(?i)^shacl$", "SHACL"),
        (r"(?i)^nextflow$", "Nextflow"),
        (r"(?i)^snakemake$", "Snakemake"),
        (r"(?i)knime\s*(workflow|work?flow\s*engine)?", "KNIME (workflow engine)"),
        (r"(?i)^lab\s*view$|^labview$", "LabVIEW"),
        (r"(?i)\bcuda\b", "CUDA"),
        (r"(?i)\bhip\b", "HIP (AMD GPU)"),
        (r"(?i)^powershell$", "PowerShell"),
        (
            r"linux\s*bash|bash\s*shell(\s*scripting)?|bash/shell (languages|scripts)|shell \(bash\)|shell\s*script(ing|s)?|^bash$|^shell$",
            "Bash/Shell",
        ),
        (r".*bash", "Bash/Shell"),
        (r"(?i)^cmake$", "CMake"),
        (r"(?i)^makefiles?$", "Makefiles"),
        (r"(?i)^m4$", "m4 (macro processor)"),
        (r"(?i)^hcl$", "HCL (HashiCorp Configuration Language)"),
        (r"(?i)^nix$", "Nix (language)"),
        (
            r"(?i)^angular$|frameworks\s*angular\s*y\s*springboot",
            "Angular / Spring Boot",
        ),
        (r"(?i)mern\s*stack", "MERN stack"),
        (r"(?i)^html$", "HTML"),
        (r"(?i)^css$", "CSS"),
        (r"(?i)^json\b", "JSON"),
        (r"(?i)^stan$", "Stan"),
        (r"(?i)^jags$", "JAGS"),
        (r"(?i)^ocaml$", "OCaml"),
        (r"(?i)^scheme$", "Scheme"),
        (r"(?i)^prolog$", "Prolog"),
        (r"(?i)^purescript$", "PureScript"),
        (r"(?i)^elm$", "Elm"),
        (r"(?i)^kotlin$", "Kotlin"),
        (r"(?i)^dart$", "Dart"),
        (r"(?i)^vhdl$", "VHDL"),
        (r"(?i)^cobol$", "COBOL"),
        (r"(?i)^latex$", "LaTeX"),
        (r"(?i)^matlab$", "MATLAB"),
        (r"(?i)^souffle$", "Soufflé (Datalog)"),
        (r"(?i)^links$", "Links (language)"),
        (r"(?i)^lablisp$", "LabLisp"),
        (r"(?i)^ansible$", "Ansible"),
        (r"(?i)^ant$", "Apache Ant"),
        (r"(?i)^dsls$", "DSLs (domain-specific languages)"),
        (r"(?i)^xql$", "XQuery/XQL"),
        (r"(?i)^hip$", "HIP (AMD GPU)"),
    ],
    "tool5": [
        (r"(?i)\bbinderhub\b", "BinderHub"),
        (r"(?i)^cran$", "CRAN (R package repository)"),
        (r"(?i)github\s*actions", "CI/CD platform (GitHub Actions)"),
        (
            r"(?i)\bk8(s)?\b|kubernetes|openshift|docker/kubernetes|spin up kubernetes pods",
            "Kubernetes/OpenShift",
        ),
        (
            r"(?i)university hosted (docker/kubernetes platforms|virtual servers)",
            "University-hosted infrastructure",
        ),
        (
            r"(?i)avionics|embedded( system)?\b|industrial pc[s]?|iot( edge)?",
            "Embedded/IoT/Edge",
        ),
        (
            '(?i)local\\s*("?cloud"?)?\\s*\\(=\\s*vms?\\)?|local virtual machines?|virtual machine.*zentraler serverinfrastruktur|\\bvms?\\b',
            "Virtual machines (local/on-prem)",
        ),
        (
            r"(?i)private\s*cloud|we have our own cloud infrastructure",
            "Private/on‑prem cloud",
        ),
        (
            r"(?i)\bgrid\b|self[- ]maintained cluster|server farms|cluster\b",
            "Clusters/Grid (on‑prem)",
        ),
        (r"(?i)^local$", "Local (on‑prem)"),
        (r"(?i)workstations?", "Workstations"),
    ],
    "train3": [
        (r"(?i)carpentr(y|ies)|software\s*carpent(y|ry)", "The Carpentries"),
        (r"(?i)code\s*refinery|coderefinery", "CodeRefinery"),
        (
            r"(?i)university (courses?|lectures?|training|provided)|standard university curriculum|postgraduate courses|msc( applied mathematics)?|bsc( applied mathematics)?|space science programme|african institute .*masters|courses? at (u[it]|university)|guest lecture|teaching (at universities|in the regular curriculum|undergraduates)|tutorial leader in physics|class(room)?|lectures?\)?|my university|universidad|universit(ä|a)tskurse|guest lecturing at university|open to ms|phd levels for applied researchers",
            "University teaching and academic courses",
        ),
        (
            r"(?i)in[- ]?house|local (ai|chapter|computer science|graduate school|institute|institution|organization|research group|scripting|staff|training|uni|university|user)|zentrumsinterne schulungen|lokale (universit(ä|a)tskurse|weiterbildungen)|provided through our organisation|offered through our organisation|our own training|we run our own training|team training|onboarding|reading group",
            "Local/in‑house trainings",
        ),
        (
            r"local|interne frameworkschulungen|private trainings|i am training phd trainees in my research laboratory|post docs. i am responsible for the material",
            "Local/in‑house trainings",
        ),
        (
            r"(?i)workshop(s)?|tutorials?( at| on)?( workshops| scientific meetings| python| agu| gem)?|user meetings|bring your own code|tutorial hackathon|hackathon(s)?|gpu hackathons|any dedicated user training workshop|dedicated totorials to interest groups",
            "Workshops, tutorials, and hackathons",
        ),
        (
            r"(?i)\bhpc\b|parallel programming|running climate models|olcf|epcc training|lumi trainings|nvidia (dli|introduction to deep learning)|pyhc workshop|reannz training|afretec workshops|chpc\b|eosc projects training|various nsf ncar efforts|tsmp fall school|grid|intersect\b",
            "HPC and research computing trainings",
        ),
        (
            r"(?i)\bgit(?!hub)\b|git (training|migration|introduction)|gitlab( introduction|/github ci/cd pipelines)?|github( actions)?|vcs\b|versionskontrolle|rse basics.*version control",
            "Version control and RSE basics",
        ),
        (
            r"(?i)python|introductot?ion to python|advanced python|advance python|teaching a course on beginner'?s programming|programming courses? for researchers|basic programming|computer science|course in computing for scientists|recode.*",
            "Python and general programming",
        ),
        (
            r"(?i)\bai\b|ai factories training|ml( software)?\b|jax behavior workshop|data (literacy|fairness|working with data)|digital literacy",
            "AI/ML and data science trainings",
        ),
        (
            r"(?i)software development (best practices)?|rse training|introduction to scientific software|workflow development|conda\b|cookiecutter|documentation (tools|management|writing)|developer training|project training|deployment\b|domain training|programming courses for researchers|google training|project pythia|escience center digital skills program|i often attend courses out on by oxford rse|tests",
            "Research software engineering practices and tools",
        ),
        (
            r"(?i)google summer of code|rladies|rse chile|galaxy training network|genomics aotearoa training|training organised by africa cdc|african institute for mathematical sciences|european materials modelling council|elwazi trainings|ncrm|zbiw|brseqtb training|project pythia|bespoke client training programms|i sometimes talk at developer meetups|other public health laboratories|research council funded training|stem innovations|training for the funded consortia that i am part of",
            "Community and external initiatives",
        ),
        (
            r"(?i)online|coursera|random youtube videos|autodidaktisch|distanzkurse der universität|self (developped|made)|developing$|formación en línea",
            "Online and self‑directed learning",
        ),
        (
            r"see https://interactivedatascience.courses/",
            "Online and self‑directed learning",
        ),
        (
            r"(?i)tu dresden|escience center|hifis education ?/ ?hida|hifis schulugen|training organised by my organisation|training at universities in federal state|offered through our organisation|local institution(s)?|local institute training|erasmus|formación company|leadership training",
            "Institution/organisation‑specific programs",
        ),
        (
            r"(?i)eln introduction|university courses on dft|genome assembly|iot workshops|mechanical engineering design|latex|linux|netdrive|conda|vcs|and gis|emerging technologies in the health field|farm machinery\)|i run training specific to our research community on tools|ci bioinformatics training|specialized for our tool|suresoft|training in our software|training on research equipment",
            "Domain- or tool-specific trainings",
        ),
        (r".* schools?|bsa reu|colegio de verano interno", "Summer/Fall schools"),
        (r"working with data|formación de data steward", "Data Management"),
        (
            r"(?i)^(n\.?a\.|none|zero|keine|ninguno)$|no\s+formal|nothing\s+formal|although it'?s not extremely structured|once$|similar$",
            None,
        ),
        (r"education program|oareidiz", None),
        (r"offering internships", None),
        (r"practicalmeeg", None),
        (r"(?i)^courses$", None),
        (r"bespoke training", None),
        (r"bespoke for field only", None),
        (r"small training groups", None),
        (r"ci\)", None),
    ],
    "train5": [
        (
            r"(?i)develop(ped|ment).*web (applications|apps|packages)|documentation and setup|software and tools.*lecture|containers",
            "Course materials/infrastructure development",
        ),
        (
            r"(?i)guest lecturer|teaching .*course section|lecture\b",
            "Lecturer / instructor",
        ),
        (r"(?i)\btutor\b", "Tutor"),
        (r"(?i)practical sessions?", "Practical/lab instructor"),
        (r"(?i)supervision", "Supervision / mentoring"),
        (r"(?i)ad hoc replacement", "Ad hoc teaching cover"),
    ],
    "ukrse3": [
        (r"(?i)with ai help|prompt for code", "AI-assisted learning"),
        (
            r"(?i)during my (own )?phd|postdoc[s]?|while working on my phd",
            "Academic research (PhD/Postdoc)",
        ),
        (
            r"(?i)apprenticeship|industrial placement",
            "Apprenticeship/industrial placement",
        ),
        (
            r"(?i)industry\b|private sector|previous (employment|industry experience)|learned on[- ]the[- ]job.*industry|previous work as consultant",
            "Industry/prior employment experience",
        ),
        (
            r"(?i)courses? (offered|organised) by (my )?employer|attending training courses while previously employed|qualifikationsma(ß|ss)nahme.*bundesagentur",
            "Employer-provided/vocational training",
        ),
        (
            r"(?i)courses offered by csc in finland|university high[- ]performance computing center staff",
            "Institutional/national HPC/RC training",
        ),
        (
            r"(?i)studium|habe informatik studiert|other school",
            "Formal education (degrees/school)",
        ),
        (
            r"(?i)you ?tube|online articles|free talks|books|stack overflow",
            "Self-directed online learning",
        ),
        (
            r"(?i)peers|co[- ]?working with a software engineer",
            "Peer learning/mentorship",
        ),
        (r"(?i)working on open source projects", "Open source contributions"),
        (
            r"(?i)i'm answering here|rather than software development generally|not in my current role in academia",
            "Other/clarification",
        ),
    ],
}
