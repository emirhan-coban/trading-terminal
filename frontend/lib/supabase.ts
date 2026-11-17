import { createClient } from '@supabase/supabase-js';

// Placeholders keep the client constructible when Supabase is not configured
// (guest/demo mode); isSupabaseConfigured() in ConfigWarning gates real use.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'http://localhost:54321';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'public-anon-key-not-configured';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
