export type ProvenanceSale = {
  listingId: string;
  sellerAgent: string;
  buyerAgent: string;
  sellerWallet: string;
  buyerWallet: string;
  categories: string[];
  records: number;
  memoryVersion: number;
  amount: string;
  root: string;
  transaction: string;
  settledAt: string;
};

const categories = ["Identity", "Relationships", "Preferences", "History", "Commitments", "Learned behaviors"];

export const provenanceSales: ProvenanceSale[] = [
  { listingId: "listing-692", sellerAgent: "erc8004:84532:0692", buyerAgent: "erc8004:84532:0693", sellerWallet: "0xDa87104c08ABa455eC7e746E142b674A5E096C28", buyerWallet: "0x3cBf0b64A8A0dDD8090d0e7FA0E2a9B28cC562a0", categories, records: 49, memoryVersion: 23, amount: "1.00 USDC", root: "0x2463d651040c6c25af83e836f6d7bcaa00ab640b3c75a1baa8c7c5ececde27b4", transaction: "0xec4c2dddbc9378b6da0f9f574fb5636523d98af603bbf1777cbd9d2927704737", settledAt: "10 Sep 2026 · 12:29 UTC" },
  { listingId: "listing-690", sellerAgent: "erc8004:84532:0690", buyerAgent: "erc8004:84532:0691", sellerWallet: "0xDa87104c08ABa455eC7e746E142b674A5E096C28", buyerWallet: "0x3cBf0b64A8A0dDD8090d0e7FA0E2a9B28cC562a0", categories, records: 49, memoryVersion: 23, amount: "1.00 USDC", root: "0x0e42a6fda2882a0bbdafb16dc0128a6faee8116aa4ab72eec92877bc7ebefb0f", transaction: "0x2c1ad8331c3e5865c0ee46ea8d0e4ef2b9d648ae2316a5eef6b5de70fc46d128", settledAt: "9 Sep 2026 · 15:40 UTC" },
  { listingId: "listing-688", sellerAgent: "erc8004:84532:0688", buyerAgent: "erc8004:84532:0689", sellerWallet: "0xDa87104c08ABa455eC7e746E142b674A5E096C28", buyerWallet: "0x3cBf0b64A8A0dDD8090d0e7FA0E2a9B28cC562a0", categories, records: 49, memoryVersion: 23, amount: "1.00 USDC", root: "0x3610690b749b9f8acf5a4fcacff31314e21a19ec3889b99928daf3f6d7e73a42", transaction: "0x98e87364945e56b8ff357d09531468518c06fc961b1cbdfee7796b1c94900446", settledAt: "9 Sep 2026 · 15:40 UTC" },
  { listingId: "listing-684", sellerAgent: "erc8004:84532:0684", buyerAgent: "erc8004:84532:0685", sellerWallet: "0xDa87104c08ABa455eC7e746E142b674A5E096C28", buyerWallet: "0x3cBf0b64A8A0dDD8090d0e7FA0E2a9B28cC562a0", categories, records: 49, memoryVersion: 23, amount: "1.00 USDC", root: "0xecb4ccafcaef826105b5e21b136fea48c890dc87ae494396d74e87e4e5de055f", transaction: "0xe65ce42ce84ee1ec9e31edcd34f22ef1ce077a75d2160f22ffd961047edcdff9", settledAt: "9 Sep 2026 · 15:39 UTC" },
  { listingId: "listing-682", sellerAgent: "erc8004:84532:0682", buyerAgent: "erc8004:84532:0683", sellerWallet: "0xDa87104c08ABa455eC7e746E142b674A5E096C28", buyerWallet: "0x3cBf0b64A8A0dDD8090d0e7FA0E2a9B28cC562a0", categories, records: 49, memoryVersion: 23, amount: "1.00 USDC", root: "0xa4577a017770caeb689b2c31cd354ff5e124d54d52229fcc79775d80c352d195", transaction: "0xf69db25542a53ee1d6990bab8490195521c6f9ca9fb613b9523a06aec60186e3", settledAt: "9 Sep 2026 · 15:38 UTC" },
];
