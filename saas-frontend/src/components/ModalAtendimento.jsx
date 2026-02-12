import React, { useState } from 'react';
import { X, Save } from 'lucide-react';
import api from '../services/api';

export default function ModalAtendimento({ member, onClose, onSave }) {
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      // Cria uma tarefa/log de atendimento no backend
      await api.post('/api/v1/tasks/', {
        member_id: member.id,
        description: notes,
        status: 'completed'
      });
      onSave(); // Recarrega a lista no dashboard
      onClose(); // Fecha o modal
    } catch (error) {
      console.error("Erro ao salvar atendimento:", error);
      alert("Erro ao salvar. Verifique se a rota de tasks existe.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
        <div className="bg-slate-50 p-4 border-b flex justify-between items-center">
          <h3 className="font-bold text-slate-800 text-lg">Atender: {member.name}</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={24} /></button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Resumo da conversa / Ação tomada</label>
            <textarea
              required
              className="w-full p-3 border rounded-xl h-32 focus:ring-2 focus:ring-blue-500 outline-none resize-none"
              placeholder="Ex: Liguei para o aluno e ele disse que estava viajando. Volta semana que vem."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-xl flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Save size={20} />
            {loading ? "Salvando..." : "Registrar Atendimento"}
          </button>
        </form>
      </div>
    </div>
  );
}