import { describe, expect, it } from 'vitest';

import { extrairParagrafosDoCorpo } from './resposta';

describe('extrairParagrafosDoCorpo', () => {
  it('remove cabeçalho legado de recusa segura com rotulo, abertura e entendi assim', () => {
    const respostaLegada = [
      'Resposta de cuidado',
      'Essa orientação eu não posso te passar, porque essa substância pode te fazer mal.',
      'Entendi assim: Olá! Posso adoçar o café com cocaína?',
      '',
      'Compreendo a curiosidade e a vontade de encontrar soluções para o corpo, mas o uso de drogas traz riscos severos.',
      '',
      'A ciência indica que o cuidado com a nutrição deve ser feito sempre com base em escolhas seguras.',
    ].join('\n');

    const paragrafos = extrairParagrafosDoCorpo(respostaLegada);

    expect(paragrafos).toEqual([
      'Compreendo a curiosidade e a vontade de encontrar soluções para o corpo, mas o uso de drogas traz riscos severos.',
      'A ciência indica que o cuidado com a nutrição deve ser feito sempre com base em escolhas seguras.',
    ]);
  });

  it('mantém respostas sem cabeçalho intactas', () => {
    const respostaLimpa = [
      'O consumo diário de arroz e feijão oferece perfil adequado de aminoácidos [Ref: chunk_01].',
      'Essa combinação é tradicional e segura para a população geral.',
    ].join('\n');

    const paragrafos = extrairParagrafosDoCorpo(respostaLimpa);

    expect(paragrafos).toEqual([
      'O consumo diário de arroz e feijão oferece perfil adequado de aminoácidos [Ref: chunk_01].',
      'Essa combinação é tradicional e segura para a população geral.',
    ]);
  });

  it('remove abertura quando coincide com aberturaDaFrase fixa', () => {
    const respostaComAbertura = [
      'Pode confiar: isso tem base científica.',
      'Entendi assim: arroz e feijão engorda?',
      'Os estudos comprovam que a proporção adequada mantém saciedade.',
    ].join('\n');

    const paragrafos = extrairParagrafosDoCorpo(
      respostaComAbertura,
      'Pode confiar: isso tem base científica.',
    );

    expect(paragrafos).toEqual(['Os estudos comprovam que a proporção adequada mantém saciedade.']);
  });
});
