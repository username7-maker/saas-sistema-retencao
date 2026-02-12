import React, { useEffect, useState, useRef } from 'react'; // Adicionado useRef
import api from '../services/api';
import { Users, AlertCircle, Search, LogOut, UploadCloud, RefreshCw } from 'lucide-react'; // Novos ícones
import ModalAtendimento from '../components/ModalAtendimento';

export default function Dashboard() {
  const [members, setMembers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false); // Estado para o upload
  const [selectedMember, setSelectedMember] = useState(null);
  const fileInputRef = useRef(null); // Referência para o input escondido

  useEffect(() => {
    fetchMembers();
  }, []);

  const fetchMembers = async () => {
    setLoading(true);
    try {
      const response = await api.get('/api/v1/members/');
      setMembers(response.data);
    } catch (error) {
      console.error("Erro ao buscar membros", error);
    } finally {
      setLoading(false);
    }
  };

  // Função para lidar com o upload do arquivo
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setIsUploading(true);
    try {
      await api.post('/api/v1/members/import-csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert("Alunos importados com sucesso!");
      fetchMembers(); // Recarrega a lista
    } catch (error) {
      console.error("Erro no upload", error);
      alert("Erro ao importar CSV. Verifique o formato do arquivo.");
    } finally {
      setIsUploading(false);
      event.target.value = null; // Limpa o input para permitir novo upload
    }
  };

  const filteredMembers = members.filter(member =>
    member.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-slate-50 p-8 font-sans text-slate-900">
      <header className="mb-8 flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
             <Users className="text-blue-600" /> Painel de Retenção
          </h1>
          <p className="text-slate-500">Gestão inteligente de cancelamentos</p>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Input de Arquivo Escondido */}
          <input 
            type="file" 
            accept=".csv" 
            className="hidden" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
          />

          {/* Botão de Importar */}
          <button 
            onClick={() => fileInputRef.current.click()}
            disabled={isUploading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-600 text-sm font-semibold rounded-xl hover:bg-blue-100 transition-all disabled:opacity-50"
          >
            {isUploading ? <RefreshCw className="animate-spin" size={18} /> : <UploadCloud size={18} />}
            {isUploading ? 'Importando...' : 'Importar CSV'}
          </button>

          <button 
            onClick={() => { localStorage.clear(); window.location.href = '/login'; }}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all"
          >
            <LogOut size={18} /> Sair
          </button>
        </div>
      </header>

      {/* Busca e Resumo */}
      <div className="flex flex-col md:flex-row gap-6 mb-8 items-end">
        <div className="bg-white p-6 rounded-2xl shadow-sm border-l-4 border-red-500 flex-1 min-w-[250px]">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-red-100 rounded-lg text-red-600">
                <AlertCircle size={24} />
            </div>
            <div>
              <p className="text-sm text-slate-500 font-semibold uppercase tracking-wider">Risco Crítico</p>
              <p className="text-3xl font-black text-slate-800">
                {members.filter(m => m.risk_level === 'red').length}
              </p>
            </div>
          </div>
        </div>

        <div className="relative flex-[2] w-full">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
          <input 
            type="text"
            placeholder="Pesquisar aluno pelo nome..."
            className="w-full pl-12 pr-4 py-4 bg-white border border-slate-200 rounded-2xl shadow-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-2xl shadow-sm overflow-hidden border border-slate-200">
        <table className="w-full text-left">
          <thead className="bg-slate-50/50 border-b border-slate-200 text-slate-500 text-sm uppercase tracking-wider">
            <tr>
              <th className="p-6 font-bold">Aluno</th>
              <th className="p-6 font-bold text-center">Status de Risco</th>
              <th className="p-6 font-bold">Último Check-in</th>
              <th className="p-6 font-bold text-center">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr><td colSpan="4" className="p-10 text-center text-slate-400">Carregando alunos...</td></tr>
            ) : filteredMembers.length > 0 ? (
              filteredMembers.map((member) => (
                <tr key={member.id} className="hover:bg-slate-50/80 transition-all group">
                  <td className="p-6 font-semibold text-slate-700">{member.name}</td>
                  <td className="p-6 text-center">
                    <span className={`px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-widest border ${
                      member.risk_level === 'red' ? 'bg-red-50 text-red-600 border-red-100' :
                      member.risk_level === 'yellow' ? 'bg-yellow-50 text-yellow-600 border-yellow-100' :
                      'bg-green-50 text-green-600 border-green-100'
                    }`}>
                      {member.risk_level}
                    </span>
                  </td>
                  <td className="p-6 text-slate-500 font-medium">
                    {member.last_checkin ? new Date(member.last_checkin).toLocaleDateString() : 'Sem registro'}
                  </td>
                  <td className="p-6 text-center">
                    <button 
                      onClick={() => setSelectedMember(member)}
                      className="px-6 py-2 bg-slate-900 text-white text-sm font-bold rounded-xl hover:bg-blue-600 transition-all transform active:scale-95 shadow-md"
                    >
                      Atender Aluno
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr><td colSpan="4" className="p-10 text-center text-slate-400">Nenhum aluno encontrado.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedMember && (
        <ModalAtendimento 
          member={selectedMember} 
          onClose={() => setSelectedMember(null)} 
          onSave={fetchMembers} 
        />
      )}
    </div>
  );
}