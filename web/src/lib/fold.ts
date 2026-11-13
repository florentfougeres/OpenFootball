/** Minuscules sans accents : compare « Zeze Steven Sessegnon » et « Steven Sessegnon » sans tenir compte de la casse ni des accents. */
export const fold = (x: string) => x.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
