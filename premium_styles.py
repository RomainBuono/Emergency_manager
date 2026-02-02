def get_premium_css():
    """
    CSS révolutionnaire hospital-grade professionnel
    Toutes les métriques système demandées par le prof
    """

    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    :root {
        --medical-blue: #0066CC;
        --medical-blue-light: #E8F3FF;
        --medical-blue-dark: #004C99;
        --critical-red: #DC2626;
        --critical-red-light: #FEE2E2;
        --urgent-orange: #F59E0B;
        --urgent-orange-light: #FEF3C7;
        --stable-green: #059669;
        --stable-green-light: #D1FAE5;
        --waiting-gray: #6B7280;
        --waiting-gray-light: #F3F4F6;
        --white: #FFFFFF;
        --gray-50: #F9FAFB;
        --gray-100: #F3F4F6;
        --gray-200: #E5E7EB;
        --gray-300: #D1D5DB;
        --gray-500: #6B7280;
        --gray-700: #374151;
        --gray-900: #111827;
        --text-primary: #111827;
        --text-secondary: #4B5563;
        --text-tertiary: #9CA3AF;
        --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        --glow-critical: 0 0 20px rgba(220, 38, 38, 0.2);
        --glow-blue: 0 0 15px rgba(0, 102, 204, 0.2);
        --radius-sm: 0.375rem;
        --radius-md: 0.5rem;
        --radius-lg: 0.75rem;
        --radius-xl: 1rem;
        --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
        --transition-base: 250ms cubic-bezier(0.4, 0, 0.2, 1);
        --font-body: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        --font-heading: 'Plus Jakarta Sans', sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }
    
    .stApp {
        background: linear-gradient(135deg, var(--gray-50) 0%, var(--white) 100%);
        font-family: var(--font-body);
        color: var(--text-primary);
    }
    
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1800px;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--white) 0%, var(--gray-50) 100%);
        border-right: 2px solid var(--gray-200);
        box-shadow: var(--shadow-lg);
    }
    
    section[data-testid="stSidebar"] > div {
        padding: 1.5rem 1rem;
    }
    
    section[data-testid="stSidebar"] h3 {
        font-family: var(--font-heading);
        font-weight: 700;
        font-size: 0.75rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-secondary);
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid var(--gray-200);
    }
    
    section[data-testid="stSidebar"] h2 {
        font-family: var(--font-mono);
        font-size: 2.5rem;
        color: var(--medical-blue);
        margin: 0;
        font-weight: 700;
    }
    
    .hero-zone {
        background: linear-gradient(135deg, rgba(0, 102, 204, 0.05) 0%, rgba(255, 255, 255, 0.8) 100%);
        border: 2px solid var(--medical-blue);
        border-radius: var(--radius-xl);
        padding: 3rem;
        margin-bottom: 2.5rem;
        box-shadow: var(--shadow-xl), var(--glow-blue);
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(10px);
    }
    
    .hero-zone::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -10%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(0, 102, 204, 0.1) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }
    
    .hero-title {
        font-family: var(--font-heading);
        font-size: 0.875rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--medical-blue);
        margin-bottom: 0.5rem;
    }
    
    .hero-subtitle {
        font-size: 1rem;
        color: var(--text-secondary);
        margin-bottom: 2rem;
        font-weight: 500;
    }
    
    .hero-kpi {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .hero-kpi-label {
        font-family: var(--font-mono);
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.1em;
        color: var(--text-tertiary);
        margin-bottom: 1rem;
    }
    
    .hero-kpi-value {
        font-family: var(--font-heading);
        font-size: 5rem;
        font-weight: 900;
        background: linear-gradient(135deg, var(--medical-blue) 0%, var(--medical-blue-dark) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1;
        margin-bottom: 1rem;
        animation: metricPulse 3s ease-in-out infinite;
    }
    
    @keyframes metricPulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    
    .hero-kpi-status {
        display: inline-block;
        padding: 0.75rem 2rem;
        border-radius: var(--radius-xl);
        font-family: var(--font-heading);
        font-weight: 700;
        font-size: 0.875rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-top: 1rem;
    }
    
    .hero-kpi-status.safe {
        background: var(--stable-green);
        color: white;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
    }
    
    .hero-kpi-status.tension {
        background: var(--urgent-orange);
        color: white;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
        animation: tensionPulse 2s ease-in-out infinite;
    }
    
    .hero-kpi-status.critical {
        background: var(--critical-red);
        color: white;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4);
        animation: criticalPulse 1.5s ease-in-out infinite;
    }
    
    @keyframes tensionPulse {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.03); opacity: 0.9; }
    }
    
    @keyframes criticalPulse {
        0%, 100% { transform: scale(1); box-shadow: 0 4px 12px rgba(220, 38, 38, 0.4); }
        50% { transform: scale(1.05); box-shadow: 0 6px 20px rgba(220, 38, 38, 0.6); }
    }
    
    .hero-metrics {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1.5rem;
        margin-top: 2rem;
    }
    
    .hero-metric {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem 1.5rem;
        background: white;
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-sm);
        font-size: 0.9375rem;
        color: var(--text-secondary);
    }
    
    .hero-metric span:first-child {
        font-size: 1.5rem;
    }
    
    .hero-metric strong {
        color: var(--medical-blue);
        font-weight: 700;
    }
    
    .critical-zone {
        background: linear-gradient(135deg, var(--critical-red-light) 0%, rgba(254, 226, 226, 0.5) 100%);
        border: 2px solid var(--critical-red);
        border-left: 6px solid var(--critical-red);
        border-radius: var(--radius-lg);
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: var(--shadow-lg), var(--glow-critical);
        animation: criticalZonePulse 3s ease-in-out infinite;
    }
    
    @keyframes criticalZonePulse {
        0%, 100% { box-shadow: var(--shadow-lg), 0 0 20px rgba(220, 38, 38, 0.2); }
        50% { box-shadow: var(--shadow-xl), 0 0 30px rgba(220, 38, 38, 0.3); }
    }
    
    .critical-alert {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.25rem;
        background: white;
        border-radius: var(--radius-md);
        margin-bottom: 0.75rem;
        box-shadow: var(--shadow-sm);
        transition: all var(--transition-fast);
    }
    
    .critical-alert:hover {
        transform: translateX(8px);
        box-shadow: var(--shadow-md);
    }
    
    .critical-alert-icon {
        font-size: 1.5rem;
        min-width: 30px;
    }
    
    .critical-alert strong {
        color: var(--critical-red);
        font-weight: 700;
    }
    
    .kpi-secondary {
        background: white;
        border: 1px solid var(--gray-200);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        box-shadow: var(--shadow-md);
        transition: all var(--transition-base);
        height: 100%;
    }
    
    .kpi-secondary:hover {
        box-shadow: var(--shadow-lg);
        transform: translateY(-4px);
        border-color: var(--medical-blue);
    }
    
    .kpi-secondary-label {
        font-family: var(--font-heading);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-secondary);
        margin-bottom: 1rem;
    }
    
    .kpi-secondary-value {
        font-family: var(--font-mono);
        font-size: 2rem;
        font-weight: 700;
        color: var(--medical-blue);
        line-height: 1;
    }
    
    .section-header {
        font-family: var(--font-heading);
        font-size: 1.5rem;
        font-weight: 800;
        color: var(--text-primary);
        margin: 2.5rem 0 1.5rem 0;
        padding: 1rem 0 1rem 1.5rem;
        border-left: 5px solid var(--medical-blue);
        background: linear-gradient(90deg, rgba(0, 102, 204, 0.08) 0%, transparent 100%);
        border-radius: var(--radius-md);
    }
    
    .section-header.critical {
        border-left-color: var(--critical-red);
        background: linear-gradient(90deg, rgba(220, 38, 38, 0.08) 0%, transparent 100%);
        color: var(--critical-red);
    }
    
    .room-card {
        background: white;
        border: 2px solid var(--gray-200);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--shadow-md);
        transition: all var(--transition-base);
    }
    
    .room-card:hover {
        box-shadow: var(--shadow-lg);
        transform: translateY(-4px);
    }
    
    .room-card.safe {
        border-left: 6px solid var(--stable-green);
        background: linear-gradient(90deg, var(--stable-green-light) 0%, white 15%);
    }
    
    .room-card.tension {
        border-left: 6px solid var(--urgent-orange);
        background: linear-gradient(90deg, var(--urgent-orange-light) 0%, white 15%);
    }
    
    .room-card.critical {
        border-left: 6px solid var(--critical-red);
        background: linear-gradient(90deg, var(--critical-red-light) 0%, white 15%);
        box-shadow: var(--shadow-lg), var(--glow-critical);
    }
    
    .room-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid var(--gray-100);
    }
    
    .room-title {
        font-family: var(--font-heading);
        font-size: 1.125rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .room-risk-label {
        padding: 0.5rem 1rem;
        border-radius: var(--radius-md);
        font-family: var(--font-mono);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    
    .room-risk-label.safe {
        background: var(--stable-green-light);
        color: var(--stable-green);
        border: 1px solid var(--stable-green);
    }
    
    .room-risk-label.tension {
        background: var(--urgent-orange-light);
        color: var(--urgent-orange);
        border: 1px solid var(--urgent-orange);
    }
    
    .room-risk-label.critical {
        background: var(--critical-red-light);
        color: var(--critical-red);
        border: 1px solid var(--critical-red);
        animation: labelPulse 2s ease-in-out infinite;
    }
    
    @keyframes labelPulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .patient-dots {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    
    .patient-dot {
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--radius-sm);
        font-size: 1.125rem;
        transition: all var(--transition-fast);
        cursor: pointer;
    }
    
    .patient-dot:hover {
        transform: scale(1.2);
    }
    
    .patient-dot.rouge {
        background: var(--critical-red-light);
        border: 2px solid var(--critical-red);
    }
    
    .patient-dot.jaune {
        background: var(--urgent-orange-light);
        border: 2px solid var(--urgent-orange);
    }
    
    .patient-dot.vert {
        background: var(--stable-green-light);
        border: 2px solid var(--stable-green);
    }
    
    .patient-dot.gris {
        background: var(--waiting-gray-light);
        border: 2px solid var(--waiting-gray);
    }
    
    .patient-dot.empty {
        background: var(--gray-100);
        border: 2px dashed var(--gray-300);
        opacity: 0.5;
    }
    
    .staff-section {
        background: white;
        border: 2px solid var(--gray-200);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        box-shadow: var(--shadow-md);
        transition: all var(--transition-base);
    }
    
    .staff-section:hover {
        box-shadow: var(--shadow-lg);
        border-color: var(--medical-blue);
    }
    
    .staff-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid var(--gray-100);
    }
    
    .staff-title {
        font-family: var(--font-heading);
        font-size: 1rem;
        font-weight: 700;
        color: var(--text-primary);
    }
    
    .staff-tension {
        padding: 0.375rem 0.875rem;
        border-radius: var(--radius-md);
        font-family: var(--font-mono);
        font-size: 0.6875rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    
    .staff-tension.safe {
        background: var(--stable-green-light);
        color: var(--stable-green);
    }
    
    .staff-tension.tension {
        background: var(--urgent-orange-light);
        color: var(--urgent-orange);
    }
    
    .staff-tension.critical {
        background: var(--critical-red-light);
        color: var(--critical-red);
        animation: labelPulse 2s ease-in-out infinite;
    }
    
    .staff-availability {
        font-family: var(--font-mono);
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-bottom: 0.75rem;
        font-weight: 600;
    }
    
    .staff-charge-bar {
        width: 100%;
        height: 8px;
        background: var(--gray-200);
        border-radius: var(--radius-md);
        overflow: hidden;
        margin-bottom: 1.5rem;
    }
    
    .staff-charge-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--stable-green), #047857);
        border-radius: var(--radius-md);
        transition: width var(--transition-base);
    }
    
    .staff-charge-fill.high {
        background: linear-gradient(90deg, var(--critical-red), #B91C1C);
    }
    
    .staff-card {
        padding: 0.875rem 1rem;
        background: var(--gray-50);
        border: 1px solid var(--gray-200);
        border-radius: var(--radius-md);
        margin-bottom: 0.625rem;
        transition: all var(--transition-fast);
    }
    
    .staff-card:hover {
        background: white;
        box-shadow: var(--shadow-sm);
        transform: translateX(6px);
    }
    
    .timeline-container {
        background: white;
        border: 2px solid var(--gray-200);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        box-shadow: var(--shadow-md);
    }
    
    .timeline-section {
        margin-bottom: 1.5rem;
    }
    
    .timeline-section:last-child {
        margin-bottom: 0;
    }
    
    .timeline-section-title {
        font-family: var(--font-heading);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: var(--text-secondary);
        margin-bottom: 1rem;
        padding: 0.5rem 0.75rem;
        background: var(--gray-100);
        border-radius: var(--radius-md);
        border-left: 4px solid var(--medical-blue);
    }
    
    .timeline-event {
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: var(--radius-md);
        font-size: 0.875rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        transition: all var(--transition-fast);
    }
    
    .timeline-event:hover {
        background: var(--gray-50);
        transform: translateX(6px);
    }
    
    .timeline-event.ai {
        background: rgba(0, 102, 204, 0.05);
        border-left: 3px solid var(--medical-blue);
    }
    
    .timeline-event.success {
        background: rgba(5, 150, 105, 0.05);
        border-left: 3px solid var(--stable-green);
    }
    
    .timeline-event.incident {
        background: rgba(220, 38, 38, 0.05);
        border-left: 3px solid var(--critical-red);
    }
    
    .timeline-time {
        font-family: var(--font-mono);
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-tertiary);
        min-width: 60px;
    }
    
    .queue-item {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 1.25rem;
        background: white;
        border: 1px solid var(--gray-200);
        border-left: 4px solid var(--medical-blue);
        border-radius: var(--radius-md);
        margin-bottom: 0.75rem;
        box-shadow: var(--shadow-sm);
        transition: all var(--transition-fast);
    }
    
    .queue-item:hover {
        box-shadow: var(--shadow-md);
        transform: translateX(8px);
        border-left-color: var(--medical-blue-dark);
    }
    
    .stButton > button {
        background: white;
        color: var(--text-primary);
        border: 2px solid var(--gray-300);
        border-radius: var(--radius-md);
        padding: 0.625rem 1.5rem;
        font-family: var(--font-body);
        font-weight: 600;
        font-size: 0.9375rem;
        transition: all var(--transition-fast);
        box-shadow: var(--shadow-sm);
    }
    
    .stButton > button:hover {
        background: var(--gray-50);
        border-color: var(--medical-blue);
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--medical-blue) 0%, var(--medical-blue-dark) 100%);
        color: white;
        border: none;
        box-shadow: 0 4px 12px rgba(0, 102, 204, 0.3);
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0052A3 0%, #003D7A 100%);
        box-shadow: 0 6px 16px rgba(0, 102, 204, 0.4);
        transform: translateY(-3px);
    }
    
    .stButton > button[kind="secondary"] {
        background: transparent;
        color: var(--medical-blue);
        border: 2px solid var(--medical-blue);
    }
    
    .stButton > button[kind="secondary"]:hover {
        background: var(--medical-blue-light);
        transform: translateY(-2px);
    }
    
    .stCheckbox label {
        font-weight: 600;
        color: var(--text-primary);
    }
    
    .stSlider > div > div > div {
        background: var(--medical-blue);
    }
    
    .stSuccess {
        background: var(--stable-green-light);
        border-left: 4px solid var(--stable-green);
        border-radius: var(--radius-md);
        padding: 1rem 1.25rem;
        color: var(--stable-green);
        font-weight: 600;
    }
    
    .stWarning {
        background: var(--urgent-orange-light);
        border-left: 4px solid var(--urgent-orange);
        border-radius: var(--radius-md);
        padding: 1rem 1.25rem;
        color: var(--urgent-orange);
        font-weight: 600;
    }
    
    .stError {
        background: var(--critical-red-light);
        border-left: 4px solid var(--critical-red);
        border-radius: var(--radius-md);
        padding: 1rem 1.25rem;
        color: var(--critical-red);
        font-weight: 600;
    }
    
    .stInfo {
        background: var(--medical-blue-light);
        border-left: 4px solid var(--medical-blue);
        border-radius: var(--radius-md);
        padding: 1rem 1.25rem;
        color: var(--medical-blue-dark);
        font-weight: 600;
    }
    
    .spacer-xs { height: 0.5rem; }
    .spacer-sm { height: 1rem; }
    .spacer-md { height: 1.5rem; }
    .spacer-lg { height: 2rem; }
    .spacer-xl { height: 3rem; }
    
    .divider {
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, var(--gray-200) 50%, transparent 100%);
        margin: 2rem 0;
    }
    
    .chatbot-container {
        background: white;
        border: 2px solid var(--gray-200);
        border-radius: var(--radius-lg);
        padding: 2rem;
        box-shadow: var(--shadow-lg);
        margin-top: 2rem;
    }
    
    .chatbot-message {
        padding: 1rem 1.25rem;
        border-radius: var(--radius-md);
        margin-bottom: 1rem;
        font-size: 0.9375rem;
        line-height: 1.6;
        animation: messageSlide 0.3s ease-out;
    }
    
    @keyframes messageSlide {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .chatbot-message.user {
        background: var(--medical-blue-light);
        color: var(--text-primary);
        margin-left: 3rem;
        border-bottom-right-radius: 4px;
    }
    
    .chatbot-message.assistant {
        background: var(--gray-100);
        color: var(--text-primary);
        margin-right: 3rem;
        border-left: 4px solid var(--stable-green);
        border-bottom-left-radius: 4px;
    }
    
    @media (max-width: 768px) {
        .main .block-container { padding: 1rem; }
        .hero-zone { padding: 2rem 1.5rem; }
        .hero-kpi-value { font-size: 3rem; }
        .hero-metrics { grid-template-columns: 1fr; }
    }
    
    *:focus-visible {
        outline: 3px solid var(--medical-blue);
        outline-offset: 2px;
    }
    
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: var(--gray-100); border-radius: var(--radius-sm); }
    ::-webkit-scrollbar-thumb { background: var(--gray-300); border-radius: var(--radius-sm); }
    ::-webkit-scrollbar-thumb:hover { background: var(--gray-500); }
    
    /* ============================================
       NAVIGATION TABS - Style boutons Play/Reset
       ============================================ */
    
    /* Container des tabs - Centré */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        background: transparent !important;
        border-bottom: none !important;
        padding: 0.5rem 0 !important;
        margin: 0 auto 2rem auto !important;
        max-width: 850px !important;
    }
    
    /* Chaque tab - Style bouton identique à Reset */
    .stTabs [data-baseweb="tab"] {
        height: 50px !important;
        min-width: 210px !important;
        flex: 1 !important;
        max-width: 260px !important;
        
        background: white !important;
        color: var(--text-primary) !important;
        border: 2px solid var(--gray-300) !important;
        border-radius: var(--radius-md) !important;
        padding: 0.625rem 1.5rem !important;
        
        font-family: var(--font-body) !important;
        font-weight: 600 !important;
        font-size: 0.9375rem !important;
        
        box-shadow: var(--shadow-sm) !important;
        transition: all var(--transition-fast) !important;
        
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        
        margin: 0 !important;
    }
    
    /* Tab au survol */
    .stTabs [data-baseweb="tab"]:hover {
        background: var(--gray-50) !important;
        border-color: var(--medical-blue) !important;
        box-shadow: var(--shadow-md) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Tab sélectionné - Style identique au bouton Play */
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--medical-blue) 0%, var(--medical-blue-dark) 100%) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0, 102, 204, 0.3) !important;
        transform: translateY(0) !important;
    }
    
    /* Tab sélectionné au survol */
    .stTabs [aria-selected="true"]:hover {
        background: linear-gradient(135deg, #0052A3 0%, #003D7A 100%) !important;
        box-shadow: 0 6px 16px rgba(0, 102, 204, 0.4) !important;
        transform: translateY(-3px) !important;
    }
    
    /* Panel de contenu */
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 1rem;
    }
    
    /* Retirer les indicateurs par défaut */
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }
    
    /* Animation d'apparition */
    @keyframes tabFadeIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .stTabs [data-baseweb="tab-list"] {
        animation: tabFadeIn 0.4s ease-out;
    }
    
    /* Focus accessibility pour tabs */
    .stTabs [data-baseweb="tab"]:focus-visible {
        outline: 3px solid var(--medical-blue) !important;
        outline-offset: 2px !important;
    }
    
    /* Responsive tabs - Tablettes */
    @media (max-width: 1024px) {
        .stTabs [data-baseweb="tab-list"] {
            max-width: 700px !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            min-width: 180px !important;
            font-size: 0.875rem !important;
        }
    }
    
    /* Responsive tabs - Mobile */
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab-list"] {
            flex-direction: column !important;
            max-width: 100% !important;
            gap: 8px !important;
        }
        
        .stTabs [data-baseweb="tab"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 100% !important;
        }
    }
    
    </style>
    """
