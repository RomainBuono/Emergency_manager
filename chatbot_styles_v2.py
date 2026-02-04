"""
🎨 CHATBOT STYLES V2 - ADAPTÉ AU STYLE PREMIUM
===============================================
Styles chatbot harmonisés avec premium_styles_v2.py
Couleurs : Bleu médical (#0066CC), pas de couleurs sombres
"""


def get_chatbot_styles_v2():
    """
    Styles CSS pour le chatbot compatibles avec premium_styles_v2.py

    HARMONISATION COMPLÈTE :
    - Couleur principale : Bleu médical (#0066CC)
    - Fond clair (blanc/gris très clair)
    - Badges verts pour statut ONLINE
    - Messages utilisateur : fond bleu clair
    - Messages assistant : fond gris clair avec bordure verte
    - Boutons actions rapides : style V2
    """

    return """
    <style>
    /* ============================================ */
    /* CHATBOT CONTAINER - STYLE V2                */
    /* ============================================ */
    
    .chatbot-container {
        background: white;
        border: 2px solid var(--gray-200);
        border-radius: var(--radius-lg);
        padding: 2rem;
        box-shadow: var(--shadow-lg);
        margin-top: 2rem;
    }
    
    /* ============================================ */
    /* CHATBOT HEADER - CARD BLEUE CLAIRE          */
    /* ============================================ */
    
    .chatbot-header {
        background: linear-gradient(135deg, var(--medical-blue-light) 0%, rgba(232, 243, 255, 0.5) 100%);
        border: 2px solid var(--medical-blue);
        border-left: 5px solid var(--medical-blue);
        border-radius: var(--radius-lg);
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--shadow-md);
    }
    
    .chatbot-header-content {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    
    .chatbot-header-left {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    
    .chatbot-icon {
        font-size: 2rem;
    }
    
    .chatbot-title {
        font-family: var(--font-heading);
        font-size: 1.75rem;
        font-weight: 800;
        color: var(--text-primary);
        margin: 0;
    }
    
    .chatbot-subtitle {
        font-size: 0.875rem;
        color: var(--text-secondary);
        margin-top: 0.25rem;
        font-weight: 500;
    }
    
    .chatbot-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        background: var(--stable-green-light);
        border: 2px solid var(--stable-green);
        border-radius: var(--radius-md);
        font-family: var(--font-mono);
        font-size: 0.8125rem;
        font-weight: 700;
        color: var(--stable-green);
        letter-spacing: 0.05em;
        box-shadow: 0 2px 6px rgba(5, 150, 105, 0.15);
    }
    
    .chatbot-status-dot {
        width: 8px;
        height: 8px;
        background: var(--stable-green);
        border-radius: 50%;
        animation: statusPulse 2s ease-in-out infinite;
    }
    
    @keyframes statusPulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(1.2); }
    }
    
    /* ============================================ */
    /* MESSAGES CHATBOT - STYLE V2                 */
    /* ============================================ */
    
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
    
    /* Message utilisateur - Bleu médical clair */
    .chatbot-message.user {
        background: var(--medical-blue-light);
        color: var(--text-primary);
        margin-left: 3rem;
        border-bottom-right-radius: 4px;
        border-left: 3px solid var(--medical-blue);
    }
    
    /* Message assistant - Gris avec bordure verte */
    .chatbot-message.assistant {
        background: var(--gray-100);
        color: var(--text-primary);
        margin-right: 3rem;
        border-left: 4px solid var(--stable-green);
        border-bottom-left-radius: 4px;
    }
    
    /* En-tête de message */
    .message-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-family: var(--font-heading);
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--text-secondary);
    }
    
    .message-content {
        color: var(--text-primary);
        line-height: 1.6;
    }
    
    /* ============================================ */
    /* ACTIONS RAPIDES - STYLE V2                  */
    /* ============================================ */
    
    .quick-actions {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin: 20px 0;
    }
    
    .quick-action-btn {
        background: white;
        border: 2px solid var(--gray-300);
        border-radius: var(--radius-md);
        padding: 12px 16px;
        color: var(--text-primary);
        font-family: var(--font-body);
        font-size: 0.9rem;
        font-weight: 600;
        cursor: pointer;
        transition: all var(--transition-fast);
        text-align: center;
        box-shadow: var(--shadow-sm);
    }
    
    .quick-action-btn:hover {
        background: var(--gray-50);
        border-color: var(--medical-blue);
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }
    
    /* ============================================ */
    /* BADGES METADATA - STYLE V2                  */
    /* ============================================ */
    
    .metadata-badge {
        display: inline-block;
        padding: 4px 10px;
        background: var(--gray-100);
        border-radius: var(--radius-sm);
        font-family: var(--font-mono);
        font-size: 0.75rem;
        margin: 4px 4px 4px 0;
        color: var(--text-secondary);
        border: 1px solid var(--gray-200);
    }
    
    .metadata-badge.success {
        background: var(--stable-green-light);
        color: var(--stable-green);
        border-color: var(--stable-green);
    }
    
    .metadata-badge.error {
        background: var(--critical-red-light);
        color: var(--critical-red);
        border-color: var(--critical-red);
    }
    
    .metadata-badge.warning {
        background: var(--urgent-orange-light);
        color: var(--urgent-orange);
        border-color: var(--urgent-orange);
    }
    
    /* ============================================ */
    /* SUMMARY PANEL - STYLE V2                    */
    /* ============================================ */
    
    .summary-panel {
        background: var(--medical-blue-light);
        border: 2px solid var(--medical-blue);
        border-left: 5px solid var(--medical-blue);
        border-radius: var(--radius-md);
        padding: 16px;
        margin-bottom: 20px;
    }
    
    .summary-text {
        color: var(--text-primary);
        font-size: 0.95rem;
        line-height: 1.5;
        font-weight: 500;
    }
    
    /* ============================================ */
    /* INPUT CHATBOT - INTÉGRÉ DANS LE CORPS      */
    /* ============================================ */
    
    .chat-input-container {
        position: relative;
        margin-top: 2rem;
        padding: 1.5rem;
        background: var(--gray-50);
        border: 2px solid var(--gray-200);
        border-radius: var(--radius-lg);
        box-shadow: var(--shadow-sm);
    }
    
    .chat-input-label {
        font-family: var(--font-heading);
        font-size: 0.875rem;
        font-weight: 700;
        color: var(--text-secondary);
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Style pour l'input Streamlit */
    .stChatInput {
        border-radius: var(--radius-md) !important;
    }
    
    .stChatInput > div {
        background: white !important;
        border: 2px solid var(--gray-300) !important;
        border-radius: var(--radius-md) !important;
    }
    
    .stChatInput > div:focus-within {
        border-color: var(--medical-blue) !important;
        box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1) !important;
    }
    
    /* ============================================ */
    /* BOUTONS SPÉCIAUX CHATBOT                    */
    /* ============================================ */
    
    .chatbot-action-button {
        background: linear-gradient(135deg, var(--medical-blue) 0%, var(--medical-blue-dark) 100%);
        color: white;
        border: none;
        border-radius: var(--radius-md);
        padding: 0.75rem 1.5rem;
        font-family: var(--font-body);
        font-weight: 700;
        font-size: 0.9375rem;
        cursor: pointer;
        transition: all var(--transition-fast);
        box-shadow: 0 4px 12px rgba(0, 102, 204, 0.3);
        width: 100%;
        margin-top: 1rem;
    }
    
    .chatbot-action-button:hover {
        background: linear-gradient(135deg, #0052A3 0%, #003D7A 100%);
        box-shadow: 0 6px 16px rgba(0, 102, 204, 0.4);
        transform: translateY(-2px);
    }
    
    .chatbot-clear-button {
        background: white;
        color: var(--critical-red);
        border: 2px solid var(--critical-red);
        border-radius: var(--radius-md);
        padding: 0.625rem 1.25rem;
        font-family: var(--font-body);
        font-weight: 600;
        font-size: 0.875rem;
        cursor: pointer;
        transition: all var(--transition-fast);
        margin-top: 1rem;
        width: 100%;
    }
    
    .chatbot-clear-button:hover {
        background: var(--critical-red-light);
        transform: translateY(-2px);
    }
    
    /* ============================================ */
    /* ANIMATIONS                                   */
    /* ============================================ */
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .fade-in {
        animation: fadeIn 0.3s ease;
    }
    
    /* ============================================ */
    /* RESPONSIVE                                   */
    /* ============================================ */
    
    @media (max-width: 768px) {
        .chatbot-message.user {
            margin-left: 1rem;
        }
        
        .chatbot-message.assistant {
            margin-right: 1rem;
        }
        
        .quick-actions {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """
