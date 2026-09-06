"""
Módulo de Inteligencia de Vacantes y Hacks de Contratación (Vacancy Booster).
Proporciona plantillas de alta conversión, palabras clave ATS indexables,
fórmulas de logros Harvard XYZ y análisis heurístico de ofertas de empleo.
"""

import re

VACANCY_BOOSTERS = {
    "ventas": {
        "id": "ventas",
        "title": "Asesor Comercial, Ventas & Cajero",
        "category_label": "🛒 Ventas, Comercio & Caja",
        "mode": "formal_boxed",
        "ats_match_score": 98,
        "keywords": [
            "Arqueo de caja", "Cierre diario", "Facturación POS", "Atención al cliente",
            "Manejo de datáfono", "Venta cruzada (cross-selling)", "Control de inventarios",
            "Fidelización de clientes", "Resolución de objeciones", "Cumplimiento de metas"
        ],
        "summary": (
            "Asesor Comercial y Cajero orientado a resultados con sólida experiencia en atención personalizada a más de "
            "60 clientes diarios, gestión de caja POS y arqueos con 100% de cuadre sin faltantes. Destacado por su habilidad "
            "en venta consultiva, cordialidad en el trato, honestidad en custodia de valores y proactividad en el surtido "
            "y exhibición estratégica de productos para maximizar la facturación del punto de venta."
        ),
        "bullets": [
            "Ejecuté cobros en efectivo, datáfonos y transferencias con registro en sistema POS, manteniendo arqueos y cierres de caja con 0% de faltantes en más de 500 jornadas operativas.",
            "Superé la meta mensual de ventas en un 18% promedio mediante asesoría consultiva, venta cruzada (cross-selling) y rápida resolución de dudas de clientes.",
            "Gestioné la recepción, etiquetado, exhibición y rotación de mercancía en góndolas, reduciendo tiempos de reposición en un 25% y manteniendo disponibilidad permanente."
        ],
        "skills_tech": "Facturación y arqueo POS, Manejo de datáfonos/terminales, Control de existencias e inventarios, Venta consultiva y cruzada",
        "skills_tools": "Terminales POS, Datáfonos inalámbricos, Software de facturación comercial, Calculadora de caja, Planillas de inventario",
        "skills_soft": "Honestidad intachable, Puntualidad rigurosa, Amabilidad y empatía, Orientación a metas comerciales, Comunicación asertiva",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** Los filtros ATS y jefes de tienda descartan CVs que solo dicen 'buena atención'. "
            "La clave para asegurar la llamada es incluir **'Arqueos de caja 100% exactos'** y **'Manejo de datáfono POS'**. "
            "Eso elimina el mayor temor del contratante: pérdidas de dinero o errores en el cobro."
        )
    },
    "admin": {
        "id": "admin",
        "title": "Auxiliar Administrativo & Recepción",
        "category_label": "📁 Administración, Oficina & Recepción",
        "mode": "formal_boxed",
        "ats_match_score": 97,
        "keywords": [
            "Gestión documental", "Radicación de facturas", "Archivo físico y digital",
            "Conmutador telefónico", "Digitación ágil", "Microsoft Excel", "Redacción corporativa",
            "Atención de conmutador", "Confidencialidad", "Control de correspondencia"
        ],
        "summary": (
            "Auxiliar Administrativo y de Oficina metódico y proactivo, con experiencia en gestión documental, radicación de "
            "facturación, atención de conmutador y recepción presencial de visitantes y proveedores. Destacado por su alta velocidad "
            "de digitación (65+ PPM), excelente ortografía, manejo de Microsoft Office y estricta confidencialidad en el tratamiento "
            "de archivos y expedientes institucionales."
        ),
        "bullets": [
            "Gestioné y radiqué más de 120 facturas y documentos corporativos semanales en archivo digital y físico, reduciendo el tiempo de localización de expedientes en un 30%.",
            "Atendí conmutador con flujo superior a 50 llamadas diarias y recepción presencial de usuarios, manteniendo un índice de satisfacción del 98% por trato cortés y ágil.",
            "Elaboré oficios formales, actas de reunión y planillas de control en Excel y Word con 0 errores ortográficos y estricta confidencialidad."
        ],
        "skills_tech": "Gestión documental y archivo, Radicación y control de facturas, Digitación ágil (65 PPM), Redacción de oficios y actas",
        "skills_tools": "Microsoft Excel/Word, Google Workspace, Escáneres y fotocopiadoras, Conmutadores telefónicos, Correo corporativo",
        "skills_soft": "Organización metódica, Discreción y ética profesional, Puntualidad estricta, Excelente presentación personal",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** No pongas solo 'manejo de computador'. Los sistemas ATS buscan términos específicos como "
            "**'Radicación de facturas'**, **'Gestión documental'** y **'Digitación ágil'**. Esas tres palabras clave te colocan "
            "de inmediato en la cima de la terna de candidatos."
        )
    },
    "bodega": {
        "id": "bodega",
        "title": "Auxiliar de Almacén, Bodega & Logística",
        "category_label": "📦 Almacén, Bodega & Despacho",
        "mode": "formal_boxed",
        "ats_match_score": 99,
        "keywords": [
            "Control de inventarios", "Método PEPS/FIFO", "Picking y packing",
            "Recepción y despacho", "Lector código de barras", "Seguridad y Salud en el Trabajo (SST)",
            "Rotulado y embalaje", "Estibador hidráulico", "Cotejo de remisiones", "Conteo cíclico"
        ],
        "summary": (
            "Auxiliar de Bodega y Logística con destreza física y rigor operativo en recepción de mercancías, descargue, "
            "alistamiento ágil de pedidos (picking/packing), rotación de inventario bajo metodología PEPS y despacho de rutas. "
            "Capacitado en normativas de Seguridad y Salud en el Trabajo (SST), orden 5S y cotejo de remisiones sin discrepancias."
        ),
        "bullets": [
            "Supervisé el descargue, verificación física y cotejo de remisiones de más de 4 toneladas semanales de mercancía, garantizando 100% de concordancia de ítems.",
            "Ejecuté picking y packing de más de 85 pedidos diarios con una tasa de precisión del 99.4%, cumpliendo estrictamente con los horarios de salida de rutas de despacho.",
            "Implementé zonificación bajo norma PEPS y 5S en estanterías, reduciendo el deterioro de producto y disminuyendo tiempos de conteo cíclico en un 20%."
        ],
        "skills_tech": "Recepción y despacho de mercancías, Conteo cíclico de inventarios, Picking y packing de precisión, Metodología PEPS/FIFO",
        "skills_tools": "Lector de código de barras / PDA, Estibador hidráulico manual, Básculas de pesaje industrial, Remisiones y planillas WMS",
        "skills_soft": "Resistencia y vitalidad física, Disciplina operativa, Puntualidad rigurosa, Compromiso con la seguridad industrial",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** El término que enamora a cualquier jefe de logística es **'Método PEPS'** (Primeras en Entrar, Primeras en Salir) "
            "y **'Precisión en picking > 99%'**. Los almacenes pierden millones en mermas; al demostrar que cuidas el inventario, eres contratado de inmediato."
        )
    },
    "servicio": {
        "id": "servicio",
        "title": "Agente de Servicio al Cliente & Call Center",
        "category_label": "🎧 Servicio al Cliente & Call Center",
        "mode": "formal_boxed",
        "ats_match_score": 98,
        "keywords": [
            "Resolución en primer contacto (FCR)", "Gestión de PQR", "Métricas CSAT/NPS",
            "Escucha activa", "Comunicación asertiva", "Sistemas CRM", "Manejo de objeciones",
            "Atención multicanal", "Fidelización", "Desescalamiento de conflictos"
        ],
        "summary": (
            "Agente de Servicio al Cliente con vocación empática, dicción clara y destreza en canales presenciales, telefónicos "
            "y digitales. Especialista en resolución rápida de PQR, desescalamiento asertivo de usuarios inconformes y sostenimiento "
            "de altos estándares de satisfacción (CSAT > 95%), logrando convertir situaciones difíciles en experiencias de lealtad."
        ),
        "bullets": [
            "Atendí un promedio de 75 interacciones diarias (llamadas, chat y presencial) logrando una tasa de resolución en primer contacto (FCR) del 89%.",
            "Gestioné, tipifiqué y di trazabilidad a casos de PQR en plataforma CRM, reduciendo los tiempos de respuesta y escalamiento en un 25%.",
            "Mantuve una calificación promedio de satisfacción del cliente (CSAT) del 96% mediante escucha activa, empatía y explicaciones claras."
        ],
        "skills_tech": "Protocolos de servicio al cliente, Gestión y tipificación de PQR, Técnicas de desescalamiento, Manejo de CRM y tickets",
        "skills_tools": "Sistemas CRM / Helpdesk, Conmutadores VoIP y diademas, Chat omnicanal, Formatos de radicación y seguimiento",
        "skills_soft": "Paciencia y autocontrol emocional, Dicción y fluidez verbal, Empatía natural, Capacidad de resolución bajo presión",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** En call center y atención presencial, los seleccionadores filtran por métricas clave: "
            "**'FCR (First Contact Resolution)'** y **'CSAT > 95%'**. Si tu CV tiene esas siglas, el reclutador sabrá que no requiere gastar semanas entrenándote."
        )
    },
    "seguridad": {
        "id": "seguridad",
        "title": "Guarda de Seguridad & Control de Accesos",
        "category_label": "🛡️ Seguridad, Vigilancia & Mantenimiento",
        "mode": "formal_boxed",
        "ats_match_score": 97,
        "keywords": [
            "Control de accesos", "Minuta de guardia", "Rondas perimetrales",
            "Monitoreo CCTV", "Prevención de pérdidas", "Detección de riesgos",
            "Atención de emergencias", "Trato respetuoso y firme", "Radiocomunicación", "Cero siniestros"
        ],
        "summary": (
            "Guarda de Seguridad y Vigilancia Privada caracterizado por disciplina férrea, honradez intachable, sentido de alerta "
            "preventiva y trato respetuoso hacia residentes, visitantes y contratistas. Amplia experiencia en control de accesos "
            "peatonales y vehiculares, rondas perimetrales, diligenciamiento pulcro de minuta y monitoreo preventivo de circuitos cerrados (CCTV)."
        ),
        "bullets": [
            "Controlé y registré minuciosamente el ingreso y salida de más de 200 personas, contratistas y automotores diarios con 100% de apego a las normas del recinto.",
            "Efectué rondas periódicas de inspección perimetral y chequeo de accesos críticos, previniendo incidentes y manteniendo un récord de 0 siniestros en el puesto.",
            "Supervisé monitores de CCTV y radiocomunicación, coordinando respuestas preventivas inmediatas con compostura y autoridad respetuosa."
        ],
        "skills_tech": "Control de accesos vehicular y peatonal, Diligenciamiento de libro de minuta, Rondas de patrullaje preventivo, Protocolos de seguridad privada",
        "skills_tools": "Libro de minuta reglamentario, Equipos de radiocomunicación UHF/VHF, Monitores de CCTV, Citofonía, Detectores de metales",
        "skills_soft": "Honradez comprobada, Estado de alerta permanente, Firmeza cortés, Puntualidad estricta, Discreción absoluta",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** Las empresas de seguridad temen a guardas descuidados o con mala actitud. "
            "Resaltar **'Récord de 0 siniestros'** y **'Diligenciamiento impecable de minuta'** es el pase directo a la firma de contrato."
        )
    },
    "transporte": {
        "id": "transporte",
        "title": "Conductor, Repartidor & Mensajería",
        "category_label": "🚗 Conductor, Reparto & Mensajería",
        "mode": "formal_boxed",
        "ats_match_score": 98,
        "keywords": [
            "Manejo defensivo", "Optimización de rutas", "Nomenclatura urbana",
            "Waze / GPS", "Recaudo contraentrega (COD)", "Puntualidad en entregas",
            "Mantenimiento preventivo", "Guías de remisión", "Cuidado de la carga", "Récord sin multas"
        ],
        "summary": (
            "Conductor y Auxiliar de Reparto Urbano responsable, puntual y con amplio conocimiento de la nomenclatura vial y rutas "
            "alternas. Experto en entrega oportuna de encomiendas y mercancías, manejo defensivo, recaudo de pagos contraentrega (COD), "
            "diligenciamiento de guías de despacho y mantenimiento preventivo del vehículo asignado."
        ),
        "bullets": [
            "Completé diariamente más de 45 entregas de paquetes con una tasa de puntualidad del 97%, planificando recorridos con GPS para reducir tiempos y consumo.",
            "Efectué recaudos de dinero contraentrega (COD) con arqueo y liquidación de planillas al 100% de exactitud y custodia rigurosa de los valores.",
            "Realicé inspecciones mecánicas preventivas diarias (niveles de fluidos, frenos y neumáticos), asegurando operatividad continua y cero infracciones de tránsito."
        ],
        "skills_tech": "Manejo defensivo y normatividad de tránsito, Optimización de rutas mediante GPS, Recaudo y cuadre contraentrega, Liquidación de guías",
        "skills_tools": "Dispositivos GPS/Waze, Aplicaciones móviles de logística y firmas, Planillas de ruta, Herramientas mecánicas básicas",
        "skills_soft": "Puntualidad rigurosa, Responsabilidad en la vía, Honestidad demostrada, Trato amable y cordial con los clientes",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** Si eres chofer o repartidor, las dos frases mágicas que buscan los jefes de flota son: "
            "**'Manejo defensivo sin comparendos'** y **'Cuadre de recaudo contraentrega al 100%'**. Te asegura la contratación sin vacilaciones."
        )
    },
    "operario": {
        "id": "operario",
        "title": "Operario de Producción & Planta Industrial",
        "category_label": "⚙️ Operario de Producción & Planta",
        "mode": "formal_boxed",
        "ats_match_score": 97,
        "keywords": [
            "Línea de ensamble continuo", "Control de calidad visual", "Normas 5S",
            "Seguridad y Salud en el Trabajo (SST)", "Cumplimiento de cuota diaria", "Empaque y sellado",
            "Uso de EPP", "Manipulación de materias primas", "Cero accidentes", "Trabajo en equipo"
        ],
        "summary": (
            "Operario de Producción Industrial dinámico, metódico y con destreza manual para desempeñarse en líneas de ensamble "
            "continuo, envasado, dosificación y empaque final de producto. Riguroso en el cumplimiento de normas de inocuidad, uso "
            "obligatorio de EPP, orden 5S y estándares de calidad para superar las cuotas diarias de manufactura."
        ),
        "bullets": [
            "Operé puestos críticos en línea de manufactura y empaque continuo, contribuyendo a alcanzar y superar el 105% de la cuota diaria programada.",
            "Efectué controles de calidad visual por muestreo, separando piezas disconformes para evitar reprocesos y garantizar la presentación final.",
            "Acaté cabalmente las normas de SST y metodología 5S en la estación asignada, registrando cero accidentes laborales en todo el periodo."
        ],
        "skills_tech": "Operación de línea continua, Control de calidad por muestreo visual, Empaque, sellado y estibado, Normas 5S y SST",
        "skills_tools": "Selladoras industriales, Balanzas de dosificación, Herramientas manuales de ensamble, Equipos de Protección Personal (EPP)",
        "skills_soft": "Agilidad y coordinación manual, Resistencia física en turnos, Disciplina y seguimiento estricto de instrucciones",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** Los jefes de planta buscan operarios que no se accidenten y cumplan la meta. "
            "Escribir **'Superación del 100% de la cuota diaria'** y **'Cero accidentes bajo normas 5S y SST'** te pone automáticamente adelante."
        )
    },
    "hosteleria": {
        "id": "hosteleria",
        "title": "Auxiliar de Cocina, Mesero & Hostelería",
        "category_label": "🍽️ Hostelería, Restaurante & Cocina",
        "mode": "formal_boxed",
        "ats_match_score": 98,
        "keywords": [
            "Buenas Prácticas de Manufactura (BPM)", "Mise en place", "Atención de comensales",
            "Toma de comandas", "Manejo de datáfono y caja", "Desinfección de áreas",
            "Servicio ágil de mesas", "Porcionado de alimentos", "Cuidado de cristalería", "Trabajo bajo presión"
        ],
        "summary": (
            "Auxiliar de Servicio Gastronómico y Mesero con excelente vocación de servicio, rapidez física y conocimientos "
            "certificados en manipulación higiénica de alimentos (BPM). Capacitado en mise en place, toma ágil de comandas, servicio "
            "amable a la mesa, manejo de sistemas de cobro y mantenimiento impecable de la salubridad en salón y cocina."
        ),
        "bullets": [
            "Atendí de forma simultánea hasta 8 mesas en horas pico de servicio, garantizando tiempos de despacho inferiores a 14 minutos y alta calidez humana.",
            "Apoyé el alistamiento previo de materias primas (mise en place), porcionado y cortes respetando al 100% las normativas sanitarias de BPM.",
            "Gestioné comanderos electrónicos y cobro de cuentas con efectivo y datáfono, recibiendo felicitaciones periódicas por servicio impecable."
        ],
        "skills_tech": "Protocolo de servicio a la mesa, Manipulación higiénica de alimentos (BPM), Mise en place y porcionado, Toma de comandas digitales",
        "skills_tools": "Comanderos electrónicos / POS, Datáfonos, Cuchillería profesional y utensilios de corte, Bandejas de servicio",
        "skills_soft": "Rapidez y dinamismo corporal, Amabilidad constante, Trabajo en equipo en horas pico, Pulcritud e higiene personal",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** El restaurante necesita saber que no enfermarás a un cliente y que no demorarás las mesas. "
            "Incluye **'Manipulación de alimentos bajo normas BPM'** y **'Tiempos de despacho < 15 minutos'** para ganarte al administrador."
        )
    },
    "primer_empleo": {
        "id": "primer_empleo",
        "title": "Candidato Primer Empleo (Sin Experiencia Previa)",
        "category_label": "🌱 Primer Empleo / Sin Experiencia",
        "mode": "formal_boxed",
        "ats_match_score": 96,
        "keywords": [
            "Rápido aprendizaje", "Puntualidad estricta (100%)", "Acatamiento de instrucciones",
            "Disponibilidad horaria total", "Trabajo en equipo", "Manejo ofimático básico",
            "Iniciativa y dinamismo", "Honradez intachable", "Actitud de servicio", "Compromiso laboral"
        ],
        "summary": (
            "Bachiller graduado disciplinado, con sólida base de valores éticos, puntualidad intachable y gran motivación para iniciar "
            "su trayectoria laboral en funciones comerciales, administrativas u operativas. Destacado por su rápida curva de aprendizaje, "
            "excelentes relaciones interpersonales, respeto estricto a las directrices de supervisión y disponibilidad inmediata."
        ),
        "bullets": [
            "Lideré y participé activamente en proyectos académicos y comunitarios, cumpliendo al 100% los plazos y pautas de entrega con alto sentido de responsabilidad.",
            "Demostré facilidad para asimilar con rapidez nuevas tecnologías, paquetería ofimática y normas operativas bajo supervisión.",
            "Mantuve una trayectoria formativa con récord de puntualidad y asistencia superior al 98%, destacando por disposición constante de superación y servicio."
        ],
        "skills_tech": "Facilidad para aprender nuevos métodos, Manejo básico de computadores y móviles, Acatamiento de protocolos",
        "skills_tools": "Microsoft Word y Excel básico, Teléfono inteligente y mensajería, Navegación web y correo electrónico",
        "skills_soft": "Puntualidad comprobada, Honradez y transparencia, Total disposición horaria, Actitud positiva y constructiva",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** El mayor error al no tener experiencia es inventar empresas falsas (las llaman y te descartan). "
            "El verdadero 'hack' es resaltar **'Puntualidad comprobada > 98%'**, **'Disponibilidad inmediata total'** y **'Facilidad para aprender'**. "
            "Los supervisores prefieren moldear a alguien con ganas que lidiar con personas con malos hábitos."
        )
    },
    "outlier_ai": {
        "id": "outlier_ai",
        "title": "AI Training Specialist & Content Evaluator (Outlier / DataAnnotation)",
        "category_label": "🤖 Outlier AI & DataAnnotation (15-25 USD/h)",
        "mode": "remote_ats",
        "ats_match_score": 99,
        "keywords": [
            "RLHF (Reinforcement Learning from Human Feedback)", "Prompt Engineering",
            "LLM Evaluation", "Fact-checking & Source Verification", "Hallucination Detection",
            "Detailed Analytical Rationales", "Rubric Compliance", "Model Benchmarking",
            "Red Teaming & Safety Assessment", "Spanish / English Native Fluency"
        ],
        "summary": (
            "AI Training Specialist and Quality Evaluator with expertise in Reinforcement Learning from Human Feedback (RLHF), "
            "LLM output assessment, and prompt engineering. Proven track record in auditing model completions for factual accuracy, "
            "logical coherence, safety, and rubric alignment, providing exhaustive written rationales in Spanish and English."
        ),
        "bullets": [
            "Evaluated and benchmarked over 450 complex LLM responses across diverse topics, applying strict RLHF rubrics to detect hallucinations and bias with a 96% audit pass rate.",
            "Authored granular analytical rationales justifying preference rankings, identifying subtle reasoning flaws, and ensuring factual grounding via cross-referenced sources.",
            "Designed adversarial test prompts (Red Teaming) to stress-test frontier conversational models, documenting edge cases and compliance vulnerabilities."
        ],
        "skills_tech": "RLHF Evaluation Frameworks, Prompt Design & Optimization, Hallucination Detection, Fact-Checking & Source Auditing",
        "skills_tools": "Frontier LLM Interfaces, Annotation Workbenches, Markdown, Google Workspace, Research Databases",
        "skills_soft": "Critical thinking, Rigorous attention to detail, Native Spanish fluency, Strong written argumentation",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** Los filtros ATS de Outlier AI y DataAnnotation buscan palabras exactas: "
            "**'RLHF'**, **'Hallucination detection'**, **'Detailed rationales'** y **'Rubric compliance'**. "
            "Sin estas palabras clave en tu CV, el algoritmo te rechaza antes de enviarte el examen de admisión."
        )
    },
    "virtual_assistant": {
        "id": "virtual_assistant",
        "title": "Bilingual Executive Assistant & Operations Coordinator",
        "category_label": "💼 Asistente Virtual Bilingüe (800-1500 USD/m)",
        "mode": "remote_ats",
        "ats_match_score": 98,
        "keywords": [
            "Calendar Management", "Executive Support", "Inbox Zero / Email Triage",
            "CRM Maintenance", "Google Workspace", "Slack / Trello / Asana",
            "Timezone Coordination", "Client Onboarding", "Confidentiality & Discretion", "Bilingual C1-C2"
        ],
        "summary": (
            "Proactive and detail-oriented Bilingual Executive Assistant (English C1 / Spanish Native) with experience providing "
            "comprehensive remote operational support to North American founders and executive teams. Skilled in multi-timezone calendar "
            "management, high-volume inbox triage, CRM maintenance, and asynchronous cross-functional communication."
        ),
        "bullets": [
            "Orchestrated complex executive calendars across EST, PST, and GMT timezones, coordinating 25+ weekly stakeholder meetings with zero scheduling conflicts.",
            "Maintained Inbox Zero across multiple executive email accounts processing 120+ daily inquiries, drafting professional correspondence in business English.",
            "Optimized client onboarding workflows within Asana and HubSpot CRM, accelerating customer turnaround times by 35%."
        ],
        "skills_tech": "Executive Calendar Management, Email Triage & Inbox Zero, CRM Pipeline Tracking, Travel & Itinerary Coordination",
        "skills_tools": "Google Workspace, Microsoft 365, Slack, Notion, Asana, Trello, Zoom, Calendly, HubSpot",
        "skills_soft": "High proactivity, Executive discretion, Exceptional cross-cultural communication, Organizational stamina",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** Plataformas como Virtual Latinos descartan automáticamente plantillas gráficas con barras de nivel de Canva. "
            "Exigen formato Harvard puro de 1 columna con **'Calendar management'**, **'Inbox Zero'** y **'English C1'**. Incluir números exactos de reuniones garantiza la entrevista."
        )
    },
    "data_evaluator": {
        "id": "data_evaluator",
        "title": "Search Quality & Data Relevance Evaluator (Appen / Telus / UHRS)",
        "category_label": "🔍 Evaluador de Búsqueda & Datos (7-15 USD/h)",
        "mode": "remote_ats",
        "ats_match_score": 98,
        "keywords": [
            "Search Query Intent", "Relevance & Authority Rating", "UHRS HitApps",
            "Spam Accuracy Rate", "Annotation Guidelines Comprehension", "Ad Quality Assessment",
            "Content Categorization", "Data Integrity", "Search Engine Quality Guidelines"
        ],
        "summary": (
            "Search Quality and Data Relevance Evaluator experienced in analyzing user query intent, assessing web page utility, "
            "and rating digital ad relevance against rigorous international guidelines. Proven ability to maintain high spam accuracy "
            "scores in fast-paced UHRS and remote crowdsourcing environments."
        ),
        "bullets": [
            "Completed over 6,000 search relevance and categorization microtasks (HitApps), maintaining an audited Spam Accuracy rate consistently above 93%.",
            "Evaluated web search results and local business listings adhering strictly to 160+ page search engine quality rating guidelines.",
            "Audited digital display ads for policy compliance, fraudulent content, and landing page quality with an average review velocity under 40 seconds."
        ],
        "skills_tech": "Search Intent Analysis, Web Relevance Rating, Guidelines Compliance, Data Tagging & Semantic Classification",
        "skills_tools": "UHRS Workbench, Search Quality Toolkits, Chrome DevTools, Excel / Google Sheets",
        "skills_soft": "Analytical precision, High self-discipline in autonomous settings, Research tenacity",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** Para que Telus o Appen te asignen proyectos de 14 USD/h, tu currículum debe mencionar "
            "**'Spam Accuracy > 92%'** y **'Quality Guidelines Compliance'**. Es la métrica que los directores de proyecto revisan para dar luz verde a tu perfil."
        )
    },
    "customer_support_remote": {
        "id": "customer_support_remote",
        "title": "Customer Experience & Technical Support Specialist",
        "category_label": "🎧 Soporte al Cliente Remoto (Zendesk / Chat)",
        "mode": "remote_ats",
        "ats_match_score": 98,
        "keywords": [
            "Zendesk", "Intercom", "SLA Compliance", "Ticket Resolution",
            "First Response Time (FRT)", "CSAT > 95%", "Remote Helpdesk",
            "Knowledge Base Authoring", "Troubleshooting", "Multichannel Support"
        ],
        "summary": (
            "Customer Experience Specialist with expertise in delivering Tier-1 and Tier-2 remote technical and billing support "
            "via chat, email, and ticketing systems. Adept at troubleshooting software workflows, maintaining SLA compliance above 98%, "
            "and sustaining high user satisfaction ratings in high-growth SaaS environments."
        ),
        "bullets": [
            "Resolved 65+ technical and billing support tickets daily in Zendesk with an average First Response Time (FRT) under 11 minutes and 98% SLA adherence.",
            "Maintained a 97% CSAT score across 1,800+ customer interactions through structured empathetic communication and swift problem resolution.",
            "Authored 16 internal and customer-facing Knowledge Base articles, reducing repeat ticket submission volume by 14%."
        ],
        "skills_tech": "Zendesk/Intercom Management, SLA & KPI Monitoring, Software Troubleshooting, Knowledge Base Creation",
        "skills_tools": "Zendesk Support, Intercom, Freshdesk, Slack, JIRA, Google Sheets",
        "skills_soft": "Empathetic communication, Patience under pressure, Rapid diagnostic reasoning",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** Los reclutadores remotos de EE.UU. buscan candidatos que conozcan **'Zendesk'**, "
            "**'SLA compliance'** y **'FRT (First Response Time)'**. Incluir estos términos reduce el filtro a cero y te coloca en la llamada final."
        )
    },
    "content_moderator": {
        "id": "content_moderator",
        "title": "Trust & Safety Content Moderator",
        "category_label": "🛡️ Moderación de Contenido USD (Trust & Safety)",
        "mode": "remote_ats",
        "ats_match_score": 98,
        "keywords": [
            "Content Moderation", "Trust & Safety", "Policy Enforcement", "Spam Detection",
            "Harmful Content Identification", "Data Confidentiality", "SLA Adherence",
            "Quality Assurance (QA)", "Queue Management", "Escalation Protocols"
        ],
        "summary": (
            "Detail-oriented and resilient Trust & Safety Content Moderator with proven experience in evaluating "
            "high-volume digital content against rigorous community guidelines and global regulatory standards. "
            "Expert in maintaining 99%+ policy precision, identifying urgent safety violations, and collaborating with cross-functional safety operations teams."
        ),
        "bullets": [
            "Audited and moderated 1,500+ daily user-generated posts, images, and videos with an average QA accuracy score of 99.1%, exceeding target SLAs.",
            "Identified, cataloged, and escalated critical policy violations and safety hazards to Tier-2 leads within 4 minutes, mitigating platform exposure.",
            "Maintained emotional resilience and strict data confidentiality under high-volume review queues while providing policy feedback to engineering leads."
        ],
        "skills_tech": "Community Guidelines Enforcement, Trust & Safety Protocols, Spam & Fraud Filtering, Quality Assurance Review",
        "skills_tools": "Internal Moderation Consoles, Zendesk Queue, JIRA, Slack, Data Annotation Platforms",
        "skills_soft": "High Emotional Resilience, Ethical Integrity, Acute Attention to Detail, Decisiveness Under Pressure",
        "recruiter_hack": (
            "💡 **HACK DE CONTRATACIÓN:** En moderación de contenido y Trust & Safety remoto, los seleccionadores buscan dos métricas: "
            "**'Policy accuracy > 98%'** y **'SLA adherence'**. Demostrar estabilidad emocional y velocidad de decisión es lo que asegura contratos en USD."
        )
    }
}


def get_vacancy_booster(booster_id: str) -> dict:
    """Retorna el booster por ID exacto o por alias común."""
    if not booster_id:
        return VACANCY_BOOSTERS["ventas"]
    clean_id = booster_id.lower().replace("job_", "").strip()
    
    # Aliases
    aliases = {
        "sales": "ventas",
        "cajero": "ventas",
        "comercial": "ventas",
        "caja": "ventas",
        "administracion": "admin",
        "recepcion": "admin",
        "asistente": "admin",
        "almacen": "bodega",
        "logistics": "bodega",
        "logistica": "bodega",
        "despacho": "bodega",
        "support": "servicio",
        "callcenter": "servicio",
        "call_center": "servicio",
        "atencion": "servicio",
        "vigilancia": "seguridad",
        "guardia": "seguridad",
        "conserje": "seguridad",
        "conductor": "transporte",
        "chofer": "transporte",
        "repartidor": "transporte",
        "mensajeria": "transporte",
        "fabrica": "operario",
        "planta": "operario",
        "produccion": "operario",
        "cocina": "hosteleria",
        "mesero": "hosteleria",
        "restaurante": "hosteleria",
        "sin_experiencia": "primer_empleo",
        "junior": "primer_empleo",
        "ai": "outlier_ai",
        "outlier": "outlier_ai",
        "dataannotation": "outlier_ai",
        "va": "virtual_assistant",
        "asistente_virtual": "virtual_assistant",
        "uhrs": "data_evaluator",
        "appen": "data_evaluator",
        "telus": "data_evaluator",
        "soporte_remoto": "customer_support_remote",
        "cx": "customer_support_remote",
        "moderador": "content_moderator",
        "moderacion": "content_moderator",
        "trust_safety": "content_moderator",
        "moderator": "content_moderator"
    }
    
    resolved_id = aliases.get(clean_id, clean_id)
    return VACANCY_BOOSTERS.get(resolved_id, None)


def analyze_job_offer(text: str) -> dict:
    """
    Analiza de forma inteligente un texto de oferta de empleo o título de vacante.
    Identifica el perfil idóneo de nuestra base de datos o sintetiza uno personalizado
    con palabras clave ATS, logros cuantitativos XYZ y el hack de contratación.
    """
    if not text or not text.strip():
        return VACANCY_BOOSTERS["ventas"]

    clean_text = text.lower()

    # Mapeo de términos fuertes hacia perfiles especializados
    match_scores = {k: 0 for k in VACANCY_BOOSTERS.keys()}

    keyword_map = {
        "ventas": ["venta", "comercial", "cajero", "caja", "pos", "datafono", "tienda", "asesor", "mostrador", "retail", "cobro"],
        "admin": ["administrativ", "recepcion", "secretari", "oficina", "radicacion", "archivo", "conmutador", "digitacion", "factura"],
        "bodega": ["bodega", "almacen", "inventario", "picking", "packing", "despacho", "mercancia", "peps", "estibador", "logistica", "carga"],
        "servicio": ["servicio al cliente", "call center", "atencion al cliente", "pqr", "reclamo", "telefonic", "csat", "fcr", "soporte presencial"],
        "seguridad": ["seguridad", "vigilante", "guarda", "cctv", "minuta", "ronda", "control de acceso", "vigilancia", "patrullaje"],
        "transporte": ["conductor", "chofer", "repartidor", "mensajer", "moto", "vehiculo", "entrega", "ruta", "flete", "manejo defensivo"],
        "operario": ["operario", "planta", "produccion", "fabrica", "ensamble", "envasado", "5s", "epp", "manufactura", "maquinaria"],
        "hosteleria": ["mesero", "cocina", "restaurante", "comida", "comanda", "barista", "camarero", "bpm", "platos", "hosteleria"],
        "primer_empleo": ["primer empleo", "sin experiencia", "aprendiz", "practicante", "estudiante", "joven", "egresado"],
        "outlier_ai": ["outlier", "rlhf", "evaluador de ia", "entrenamiento ia", "prompt", "llm", "dataannotation", "alignerr", "inteligencia artificial"],
        "virtual_assistant": ["asistente virtual", "virtual assistant", "virtual latinos", "calendar", "inbox zero", "bilingual", "bilingue", "agenda"],
        "data_evaluator": ["appen", "telus", "uhrs", "clickworker", "relevancia", "search evaluator", "anotacion", "oneforma"],
        "customer_support_remote": ["zendesk", "intercom", "soporte remoto", "ticket", "sla", "customer experience", "helpdesk"],
        "content_moderator": ["moderador", "moderacion", "content moderator", "trust & safety", "trust and safety", "politicas de contenido", "moderator", "safety reviewer"]
    }

    for booster_id, terms in keyword_map.items():
        for t in terms:
            if t in clean_text:
                match_scores[booster_id] += 3
            # Bonus por palabras exactas
            pattern = rf"\b{re.escape(t)}\b"
            if re.search(pattern, clean_text):
                match_scores[booster_id] += 2

    # Obtener el mejor puntaje
    best_booster_id = max(match_scores, key=match_scores.get)
    highest_score = match_scores[best_booster_id]

    if highest_score >= 3:
        matched = VACANCY_BOOSTERS[best_booster_id].copy()
        # Si el texto es una oferta específica o un título personalizado, enriquecer el título
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        first_line = lines[0] if lines else ""
        if len(first_line) <= 55 and not any(kw in first_line.lower() for kw in ["buscamos", "oferta", "importante empresa", "convocatoria"]):
            matched["custom_title"] = first_line.title()
        return matched

    # Si no hubo coincidencia fuerte con un cargo estándar, sintetizar un Booster Inteligente Personalizado
    # Extraer el posible cargo del texto limpiando muletillas comunes
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    raw_title = lines[0] if lines else "Especialista Operativo & Profesional"
    
    clean_title = raw_title
    for prefix_pat in [
        r"^(?:se\s+busca|buscamos|requerimos|se\s+solicita|se\s+requiere|convocatoria\s+para|oferta\s+(?:de\s+)?empleo\s+(?:para)?|vacante\s+(?:de)?|importante\s+empresa\s+busca)\s*:?\s*",
        r"^(?:urgente\s*:?\s*)",
    ]:
        clean_title = re.sub(prefix_pat, "", clean_title, flags=re.IGNORECASE).strip()

    for sep in [" - ", " | ", ",", " para ", " en "]:
        if sep in clean_title:
            part = clean_title.split(sep)[0].strip()
            if len(part) >= 4:
                clean_title = part
                break

    if len(clean_title) > 50:
        clean_title = clean_title[:47].rstrip() + "..."

    if not clean_title or len(clean_title) < 3:
        clean_title = "Especialista Operativo & Profesional"

    custom_title = clean_title.title()

    return {
        "id": "custom",
        "title": custom_title,
        "category_label": f"🎯 Perfil a Medida: {custom_title}",
        "mode": "formal_boxed",
        "ats_match_score": 96,
        "keywords": [
            "Cumplimiento de objetivos", "Optimización de procesos", "Atención al detalle",
            "Gestión operativa", "Trabajo bajo presión", "Reportes y trazabilidad",
            "Normas institucionales", "Puntualidad comprobada", "Resolución de problemas"
        ],
        "summary": (
            f"Profesional responsable y calificado en el área de {custom_title}, con amplia experiencia en cumplimiento de objetivos "
            f"operativos, aplicación de protocolos de calidad y orientación a la satisfacción del cliente interno y externo. "
            f"Caracterizado por su alto sentido de compromiso ético, adaptabilidad a metodologías corporativas y puntualidad intachable."
        ),
        "bullets": [
            f"Lideré y ejecuté las actividades clave de {custom_title}, superando las metas de desempeño fijadas en un 15% mediante optimización sistemática de tareas.",
            "Implementé controles de calidad y seguimiento riguroso en procedimientos operativos, asegurando un índice de cumplimiento del 99% sin desvíos.",
            "Fomenté una cultura de comunicación constructiva, trabajo en equipo y atención oportuna a solicitudes de usuarios y supervisión."
        ],
        "skills_tech": f"Procedimientos técnicos de {custom_title}, Control de calidad y seguimiento, Elaboración de reportes de gestión",
        "skills_tools": "Herramientas especializadas del cargo, Software ofimático, Sistemas de gestión operativa",
        "skills_soft": "Puntualidad estricta, Honestidad demostrada, Alta capacidad de resolución, Trabajo en equipo multidisciplinario",
        "recruiter_hack": (
            f"💡 **HACK DE CONTRATACIÓN:** Para la vacante de **{custom_title}**, los reclutadores buscan métricas cuantificables "
            "y fórmulas de acción 'Logré X mediante Y logrando Z%'. Al sustituir descripciones vagas por metas del 99%, tu CV sobresale sobre el 90% de los aspirantes."
        )
    }
