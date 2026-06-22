// Vite-specific import query suffixes — ambient type declarations for tsc.
// These are handled at build time by Vite; tsc only needs to know the types.

declare module "*.css?inline" {
  const content: string;
  export default content;
}

declare module "*.css?raw" {
  const content: string;
  export default content;
}

declare module "*.svg?raw" {
  const content: string;
  export default content;
}

declare module "*.svg?url" {
  const content: string;
  export default content;
}
