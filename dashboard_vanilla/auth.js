/**
 * auth.js - Handles Supabase Authentication and Database initialization.
 * 
 * IMPORTANT: Replace these placeholders with your actual Supabase Project URL and Anon Key!
 */

const SUPABASE_URL = 'YOUR_SUPABASE_URL_HERE';
const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY_HERE';

let supabaseClient = null;
let currentUser = null;

// Initialize Supabase if keys are provided
if (SUPABASE_URL !== 'YOUR_SUPABASE_URL_HERE' && typeof supabase !== 'undefined') {
    supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
}

// Ensure the UI is ready before hooking up auth elements
document.addEventListener('DOMContentLoaded', async () => {
    if (!supabaseClient) {
        console.warn("Supabase not initialized. Please set your keys in auth.js.");
        return;
    }

    // Check for active session
    const { data: { session } } = await supabaseClient.auth.getSession();
    handleSession(session);

    // Listen for auth state changes
    supabaseClient.auth.onAuthStateChange((_event, session) => {
        handleSession(session);
    });

    // Hook up login form
    const loginForm = document.getElementById('form-login');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('input-email').value;
            const password = document.getElementById('input-password').value;
            const isSignUp = document.getElementById('toggle-signup').checked;

            try {
                if (isSignUp) {
                    const { error } = await supabaseClient.auth.signUp({ email, password });
                    if (error) throw error;
                    alert("Sign up successful! You are now logged in.");
                } else {
                    const { error } = await supabaseClient.auth.signInWithPassword({ email, password });
                    if (error) throw error;
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            }
        });
    }

    // Hook up logout button
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) {
        btnLogout.addEventListener('click', async () => {
            await supabaseClient.auth.signOut();
        });
    }
});

function handleSession(session) {
    currentUser = session ? session.user : null;
    const loginOverlay = document.getElementById('modal-login');
    const appHeader = document.getElementById('app-header');
    
    if (currentUser) {
        // Logged in
        if (loginOverlay) loginOverlay.style.display = 'none';
        const userEmailDisplay = document.getElementById('user-email');
        if (userEmailDisplay) userEmailDisplay.textContent = currentUser.email;
        document.body.classList.remove('logged-out');
        // Trigger initial data load
        if (typeof refresh === 'function') refresh();
    } else {
        // Logged out
        if (loginOverlay) loginOverlay.style.display = 'flex';
        document.body.classList.add('logged-out');
    }
}
