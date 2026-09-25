/**
 * Remove linhas de cabeçalho redundantes da resposta que já são exibidas pelo CardDeVeredito
 * (rótulo do veredito, frase de abertura e alegação "Entendi assim:").
 */
export function extrairParagrafosDoCorpo(answer: string, aberturaFixa?: string): string[] {
  const linhas = answer
    .split('\n')
    .map((linha) => linha.trim())
    .filter(Boolean);

  let inicio = 0;
  while (inicio < linhas.length && inicio < 3) {
    const linha = linhas[inicio];
    const ehRotulo = /^Resposta (de cuidado|informativa|sobre o mito)/i.test(linha);
    const ehEntendiAssim = /^Entendi assim:/i.test(linha);
    const ehAbertura =
      (aberturaFixa && linha === aberturaFixa) ||
      /^(Essa?|Esse?|O uso) .* (pode te fazer mal|riscos graves|riscos sérios)\.?$/i.test(linha);

    if (ehRotulo || ehEntendiAssim || ehAbertura) {
      inicio++;
    } else {
      break;
    }
  }

  return linhas.slice(inicio);
}
