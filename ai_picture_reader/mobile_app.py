 col1, col2 = st.columns(2)
            with col1:
                if st.button("Send Reset Link", use_container_width=True):
                    try:
                        supabase.auth.reset_password_for_email(
                            reset_email,
                            options={"redirect_to": "https://ai-vision-scanner.onrender.com"}
                        )
                        st.success("Reset link sent! Please check your email inbox.")
                    except Exception as e:
                        st.error(f"Error: {e}")
            with col2:
                if st.button("Back to Login", use_container_width=True):
                    st.session_state.reset_mode = False
                    st.rerun()
                
