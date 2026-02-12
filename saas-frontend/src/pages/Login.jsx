import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { Lock, Mail, Loader2 } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Preparando os dados no formato OAuth2 que o seu auth.py espera
    const formData = new FormData();
    formData.append('username', email); // O FastAPI usa 'username' como padrão para o e-mail
    formData.append('password', password);

    try {
      // ATENÇÃO: Rota corrigida de /token para /login para bater com seu auth.py
      const response = await api.post('/api/v1/auth/login', formData);
      
      // Salva o token JWT no navegador
      localStorage.setItem('token', response.data.access_token);
      
      // Se deu certo, vai para o dashboard
      navigate('/dashboard');
    } catch (err) {
      console.error("Erro no login:", err.response);
      if (err.response && err.response.status === 401) {
        setError('E-mail ou senha incorretos.');
      } else {
        setError('Erro ao conectar com o servidor. Verifique se o Backend está ligado.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 border border-slate-200">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-slate-800 tracking-tight">AI Gym OS</h2>
          <p className="text-slate-500 mt-2 text-sm">Sistema Inteligente de Retenção</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">E-mail</label>
            <div className="relative">
              <Mail className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
              <input
                type="email"
                required
                className="pl-10 w-full p-3 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-1">Senha</label>
            <div className="relative">
              <Lock className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
              <input
                type="password"
                required
                className="pl-10 w-full p-3 bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <div className="bg-red-50 text-red-600 text-sm p-3 rounded-lg text-center font-medium border border-red-100">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg shadow-lg shadow-blue-200 transition-all flex items-center justify-center disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin mr-2 h-5 w-5" />
                Autenticando...
              </>
            ) : (
              'Entrar no Sistema'
            )}
          </button>
        </form>

        <p className="text-center mt-6 text-xs text-slate-400">
          Acesso restrito a administradores.
        </p>
      </div>
    </div>
  );
}