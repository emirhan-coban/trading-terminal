import type { Metadata } from 'next';
import './globals.css';
import LocaleTranslator from '@/components/LocaleTranslator';
import BackendStatus from '@/components/BackendStatus';
export const metadata:Metadata={title:'NEXUS — Multi-Asset Trading Terminal',description:'Research and paper-trading terminal for crypto, US stocks and BIST. Paper trading only, not investment advice.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="tr"><body><LocaleTranslator/><BackendStatus/>{children}</body></html>}
