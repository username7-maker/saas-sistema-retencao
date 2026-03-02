import { api } from "./api";

export const lgpdService = {
  async exportMemberPdf(memberId: string): Promise<void> {
    const { data } = await api.get(`/api/v1/lgpd/export/member/${memberId}`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([data as BlobPart]));
    const link = document.createElement("a");
    link.href = url;
    link.download = `dados_membro_${memberId}.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  },

  async anonymizeMember(memberId: string): Promise<void> {
    await api.post(`/api/v1/lgpd/anonymize/member/${memberId}`);
  },
};
