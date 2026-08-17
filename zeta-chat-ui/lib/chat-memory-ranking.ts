type RankableMemoryDocument = {
  text: string;
  importance: number;
  createdAt: string;
};

type PreparedDocument<TDocument extends RankableMemoryDocument> = {
  document: TDocument;
  tokens: string[];
  counts: Map<string, number>;
  length: number;
};

type PreparedIndex<TDocument extends RankableMemoryDocument> = {
  documents: Array<PreparedDocument<TDocument>>;
  documentFrequency: Map<string, number>;
  averageLength: number;
};

const preparedIndexCache = new WeakMap<
  RankableMemoryDocument[],
  PreparedIndex<RankableMemoryDocument>
>();

export function rankMemoryDocuments<TDocument extends RankableMemoryDocument>(
  documents: TDocument[],
  query: string,
) {
  const queryTokens = Array.from(new Set(tokenize(query)));
  if (!queryTokens.length) {
    return rankRecentImportant(documents);
  }

  const index = getPreparedIndex(documents);
  const ranked = index.documents
    .map((prepared) => {
      let lexicalScore = 0;
      for (const token of queryTokens) {
        const frequency = prepared.counts.get(token) ?? 0;
        if (!frequency) {
          continue;
        }
        lexicalScore += bm25Score({
          frequency,
          documentFrequency: index.documentFrequency.get(token) ?? 0,
          documentCount: index.documents.length,
          documentLength: prepared.length,
          averageLength: index.averageLength,
        });
      }

      return {
        document: prepared.document,
        lexicalScore,
        score: lexicalScore + recencyAdjustedImportance(prepared.document),
      };
    })
    .filter((item) => item.lexicalScore > 0)
    .sort((left, right) => right.score - left.score)
    .map((item) => item.document);

  return ranked.length ? ranked : rankRecentImportant(documents);
}

function getPreparedIndex<TDocument extends RankableMemoryDocument>(
  documents: TDocument[],
) {
  const cached = preparedIndexCache.get(documents as RankableMemoryDocument[]);
  if (cached) {
    return cached as PreparedIndex<TDocument>;
  }

  const preparedDocuments = documents.map((document) => {
    const tokens = tokenize(document.text);
    const counts = new Map<string, number>();
    for (const token of tokens) {
      counts.set(token, (counts.get(token) ?? 0) + 1);
    }

    return {
      document,
      tokens,
      counts,
      length: Math.max(1, tokens.length),
    };
  });
  const documentFrequency = new Map<string, number>();
  for (const prepared of preparedDocuments) {
    for (const token of new Set(prepared.tokens)) {
      documentFrequency.set(token, (documentFrequency.get(token) ?? 0) + 1);
    }
  }
  const averageLength =
    preparedDocuments.reduce((sum, document) => sum + document.length, 0) /
      Math.max(1, preparedDocuments.length) || 1;
  const index = {
    documents: preparedDocuments,
    documentFrequency,
    averageLength,
  };

  preparedIndexCache.set(
    documents as RankableMemoryDocument[],
    index as PreparedIndex<RankableMemoryDocument>,
  );

  return index;
}

function tokenize(input: string) {
  const tokens: string[] = [];
  const lower = input.toLowerCase();

  for (const token of lower.match(/[a-z0-9\uac00-\ud7a3]{2,}/g) ?? []) {
    tokens.push(token);
  }

  const compactKorean = lower.replace(/[^\uac00-\ud7a3]/g, "");
  for (let index = 0; index < compactKorean.length - 1; index += 1) {
    tokens.push(compactKorean.slice(index, index + 2));
  }

  return tokens;
}

function bm25Score(input: {
  frequency: number;
  documentFrequency: number;
  documentCount: number;
  documentLength: number;
  averageLength: number;
}) {
  const k1 = 1.2;
  const b = 0.75;
  const idf = Math.log(
    1 +
      (input.documentCount - input.documentFrequency + 0.5) /
        (input.documentFrequency + 0.5),
  );
  const denominator =
    input.frequency +
    k1 *
      (1 - b + b * (input.documentLength / Math.max(1, input.averageLength)));

  return idf * ((input.frequency * (k1 + 1)) / denominator);
}

function rankRecentImportant<TDocument extends RankableMemoryDocument>(
  documents: TDocument[],
) {
  return documents
    .slice(-8)
    .sort(
      (left, right) =>
        recencyAdjustedImportance(right) - recencyAdjustedImportance(left),
    );
}

function recencyAdjustedImportance(document: RankableMemoryDocument) {
  return document.importance * recencyDecay(document.createdAt);
}

function recencyDecay(createdAt: string) {
  const created = Date.parse(createdAt);
  if (!Number.isFinite(created)) {
    return 0.5;
  }

  const ageDays = Math.max(0, (Date.now() - created) / 86_400_000);
  const lambda = getNonNegativeNumberEnv("MEMORY_RECENCY_DECAY_LAMBDA", 0.03);
  return Math.exp(-lambda * ageDays);
}

function getNonNegativeNumberEnv(name: string, fallback: number) {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value >= 0 ? value : fallback;
}
