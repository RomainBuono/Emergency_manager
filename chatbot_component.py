"""
🤖 CHATBOT PREMIUM COMPONENT
=============================
Chatbot IA intégré avec design premium pour le dashboard V2
"""

import streamlit as st
from typing import Optional, Dict, Any, List


def render_chatbot_premium(
    chatbot_available: bool,
    chatbot_instance: Optional[Any],
    chat_history: List[Dict],
    on_message_callback
) -> None:
    """
    Affiche le chatbot avec design premium.
    
    Args:
        chatbot_available: Si le module chatbot est disponible
        chatbot_instance: Instance du ChatbotEngine
        chat_history: Historique des messages
        on_message_callback: Fonction appelée lors d'un nouveau message
    """
    
    # CSS Chatbot Premium
    st.markdown("""
        <style>
        /* Container chatbot */
        .chatbot-container {
            background: linear-gradient(135deg, rgba(30, 33, 41, 0.9) 0%, rgba(14, 17, 23, 0.9) 100%);
            border: 1px solid rgba(102, 126, 234, 0.2);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
        }
        
        /* Header chatbot */
        .chatbot-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .chatbot-title {
            font-size: 1.4rem;
            font-weight: 700;
            color: #FAFAFA;
            margin: 0;
        }
        
        .chatbot-status {
            display: inline-block;
            padding: 4px 12px;
            background: rgba(0, 208, 132, 0.2);
            border: 1px solid var(--stable);
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--stable);
            animation: gentlePulse 2s ease-in-out infinite;
        }
        
        /* Messages */
        .chat-message {
            margin: 16px 0;
            padding: 16px 20px;
            border-radius: 12px;
            animation: fadeIn 0.3s ease;
        }
        
        .chat-message.user {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(102, 126, 234, 0.05) 100%);
            border-left: 3px solid var(--accent);
            margin-left: 40px;
        }
        
        .chat-message.assistant {
            background: linear-gradient(135deg, rgba(0, 208, 132, 0.1) 0%, rgba(0, 208, 132, 0.02) 100%);
            border-left: 3px solid var(--stable);
            margin-right: 40px;
        }
        
        .message-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-secondary);
        }
        
        .message-content {
            color: var(--text-primary);
            line-height: 1.6;
        }
        
        /* Quick actions */
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin: 20px 0;
        }
        
        .quick-action-btn {
            background: rgba(30, 33, 41, 0.6);
            border: 1px solid rgba(102, 126, 234, 0.2);
            border-radius: 10px;
            padding: 12px 16px;
            color: var(--text-primary);
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: left;
        }
        
        .quick-action-btn:hover {
            background: rgba(102, 126, 234, 0.15);
            border-color: var(--accent);
            transform: translateY(-2px);
        }
        
        /* Metadata badges */
        .metadata-badge {
            display: inline-block;
            padding: 4px 10px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            font-size: 0.75rem;
            margin: 4px 4px 4px 0;
            color: var(--text-secondary);
        }
        
        .metadata-badge.success {
            background: rgba(0, 208, 132, 0.15);
            color: var(--stable);
        }
        
        .metadata-badge.error {
            background: rgba(255, 75, 75, 0.15);
            color: var(--critical);
        }
        
        /* Summary panel */
        .summary-panel {
            background: rgba(102, 126, 234, 0.1);
            border: 1px solid rgba(102, 126, 234, 0.3);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 20px;
        }
        
        .summary-text {
            color: var(--text-primary);
            font-size: 0.95rem;
            line-height: 1.5;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Container principal
    st.markdown('<div class="chatbot-container">', unsafe_allow_html=True)
    
    # Header
    st.markdown('''
        <div class="chatbot-header">
            <div style="font-size: 2rem;">🤖</div>
            <div class="chatbot-title">AI Assistant</div>
            <div class="chatbot-status">● ONLINE</div>
        </div>
    ''', unsafe_allow_html=True)
    
    # Vérifications
    if not chatbot_available:
        st.error("❌ Module chatbot non disponible. Vérifiez l'installation.")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    if chatbot_instance is None:
        st.warning("⚠️ Chatbot non initialisé. Clé API Mistral manquante ?")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # Résumé système
    try:
        summary = chatbot_instance.get_system_summary()
        st.markdown(f'''
            <div class="summary-panel">
                <div class="summary-text">
                    <strong>📊 État du système :</strong> {summary}
                </div>
            </div>
        ''', unsafe_allow_html=True)
    except:
        pass
    
    # Zone de messages
    st.markdown('<div style="margin: 20px 0; max-height: 500px; overflow-y: auto;">', unsafe_allow_html=True)
    
    for msg in chat_history:
        role = msg["role"]
        content = msg["content"]
        
        # Message utilisateur
        if role == "user":
            st.markdown(f'''
                <div class="chat-message user">
                    <div class="message-header">
                        <span>👤</span>
                        <span>Vous</span>
                    </div>
                    <div class="message-content">{content}</div>
                </div>
            ''', unsafe_allow_html=True)
        
        # Message assistant
        else:
            st.markdown(f'''
                <div class="chat-message assistant">
                    <div class="message-header">
                        <span>🤖</span>
                        <span>AI Assistant</span>
                    </div>
                    <div class="message-content">{content}</div>
                </div>
            ''', unsafe_allow_html=True)
            
            # Métadonnées (optionnel)
            if msg.get("metadata"):
                meta = msg["metadata"]
                
                # Guardrail status
                if meta.get("guardrail_status") == "blocked":
                    st.markdown(f'''
                        <div style="margin-top: 8px;">
                            <span class="metadata-badge error">
                                🛡️ Bloqué : {meta.get('guardrail_details', 'Violation détectée')}
                            </span>
                        </div>
                    ''', unsafe_allow_html=True)
                
                # Actions exécutées
                if meta.get("actions_executed"):
                    actions_html = ""
                    for action in meta["actions_executed"]:
                        status_class = "success" if action.get("success") else "error"
                        icon = "✅" if action.get("success") else "❌"
                        actions_html += f'<span class="metadata-badge {status_class}">{icon} {action.get("tool", "Action")}</span>'
                    
                    st.markdown(f'<div style="margin-top: 8px;">{actions_html}</div>', unsafe_allow_html=True)
                
                # Latence
                if meta.get("latency_ms"):
                    st.markdown(f'''
                        <div style="margin-top: 8px; font-size: 0.75rem; color: var(--text-secondary);">
                            ⚡ {meta["latency_ms"]:.0f}ms
                        </div>
                    ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input utilisateur
    user_input = st.chat_input("💬 Posez votre question ou donnez une commande...")
    
    if user_input:
        on_message_callback(user_input)
    
    # Actions rapides
    st.markdown('<div style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 12px;">⚡ Actions rapides :</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 État système", use_container_width=True, key="quick_status"):
            on_message_callback("Quel est l'état du système ?")
    
    with col2:
        if st.button("👥 Liste patients", use_container_width=True, key="quick_patients"):
            on_message_callback("Liste les patients")
    
    with col3:
        if st.button("➕ Ajouter patient", use_container_width=True, key="quick_add"):
            on_message_callback("Ajoute 1 patient jaune avec douleur abdominale")
    
    with col4:
        if st.button("🤖 Dernière décision", use_container_width=True, key="quick_decision"):
            on_message_callback("Explique la dernière décision de l'agent")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Bouton effacer
    if st.button("🗑️ Effacer conversation", use_container_width=True, key="clear_chat"):
        st.session_state.chat_history = []
        if chatbot_instance:
            try:
                chatbot_instance.clear_conversation()
            except:
                pass
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def initialize_chatbot(controller, state, decision_history):
    """
    Initialise le chatbot avec les dépendances nécessaires.
    
    Args:
        controller: EmergencyController
        state: EmergencyState
        decision_history: Liste de l'historique des décisions
    
    Returns:
        ChatbotEngine instance ou None
    """
    try:
        # Import LOCAL pour éviter les erreurs au chargement du module
        import sys
        from pathlib import Path
        
        # Vérifier que le module existe
        chatbot_path = Path(__file__).parent / "chatbot"
        if not chatbot_path.exists():
            print(f"❌ Dossier chatbot introuvable : {chatbot_path}")
            return None
        
        # Import dynamique
        from chatbot.chatbot_engine import ChatbotEngine
        
        print("✅ ChatbotEngine importé avec succès dans initialize_chatbot")
        
        chatbot = ChatbotEngine(
            controller=controller,
            state=state,
            decision_history_ref=decision_history
        )
        
        print("✅ ChatbotEngine initialisé avec succès")
        return chatbot
    
    except ImportError as e:
        print(f"❌ Module chatbot non disponible : {e}")
        import traceback
        traceback.print_exc()
        return None
    
    except Exception as e:
        print(f"❌ Erreur initialisation chatbot : {e}")
        import traceback
        traceback.print_exc()
        return None