import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Search, Plus, Trash2, ChevronDown, ChevronRight, Clock, Layers, MessageSquare, 
    Bell, Calendar, Rss, Grid, HelpCircle, X
} from 'lucide-react';

// ─── TradingView-style Symbol Database ─────────────────────────────────────────
const SYMBOL_DATABASE = [
    // Forex — dual flag: base (logoImg) + quote (logoImg2)
    { symbol: 'FX:EURUSD',       name: 'EURUSD',   full: 'Euro / U.S. Dollar',             type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/eu.png',  logoImg2: 'https://flagcdn.com/h24/us.png',  logoBg: '#089981', isPositive: true },
    { symbol: 'FX:GBPUSD',       name: 'GBPUSD',   full: 'GBP / U.S. Dollar',              type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/gb.png',  logoImg2: 'https://flagcdn.com/h24/us.png',  logoBg: '#1e54e4', isPositive: false },
    { symbol: 'FX:USDJPY',       name: 'USDJPY',   full: 'USD / Japanese Yen',             type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/us.png',  logoImg2: 'https://flagcdn.com/h24/jp.png',  logoBg: '#dc2626', isPositive: true },
    { symbol: 'FX:USDCHF',       name: 'USDCHF',   full: 'USD / Swiss Franc',              type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/us.png',  logoImg2: 'https://flagcdn.com/h24/ch.png',  logoBg: '#2563eb', isPositive: false },
    { symbol: 'FX:USDCAD',       name: 'USDCAD',   full: 'USD / Canadian Dollar',          type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/us.png',  logoImg2: 'https://flagcdn.com/h24/ca.png',  logoBg: '#dc2626', isPositive: false },
    { symbol: 'FX:AUDUSD',       name: 'AUDUSD',   full: 'Australian Dollar / USD',        type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/au.png',  logoImg2: 'https://flagcdn.com/h24/us.png',  logoBg: '#d97706', isPositive: true },
    { symbol: 'FX:NZDUSD',       name: 'NZDUSD',   full: 'NZD / U.S. Dollar',              type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/nz.png',  logoImg2: 'https://flagcdn.com/h24/us.png',  logoBg: '#f23645', isPositive: false },
    { symbol: 'FX:EURAUD',       name: 'EURAUD',   full: 'EUR / Australian Dollar',        type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/eu.png',  logoImg2: 'https://flagcdn.com/h24/au.png',  logoBg: '#089981', isPositive: true },
    { symbol: 'FX:EURGBP',       name: 'EURGBP',   full: 'Euro / British Pound',           type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/eu.png',  logoImg2: 'https://flagcdn.com/h24/gb.png',  logoBg: '#7c3aed', isPositive: false },
    { symbol: 'FX:GBPJPY',       name: 'GBPJPY',   full: 'GBP / Japanese Yen',             type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/gb.png',  logoImg2: 'https://flagcdn.com/h24/jp.png',  logoBg: '#b91c1c', isPositive: false },
    { symbol: 'FX:EURJPY',       name: 'EURJPY',   full: 'Euro / Japanese Yen',            type: 'forex',    exchange: 'FX',        logoImg: 'https://flagcdn.com/h24/eu.png',  logoImg2: 'https://flagcdn.com/h24/jp.png',  logoBg: '#db2777', isPositive: true },
    // Crypto
    { symbol: 'BINANCE:BTCUSDT', name: 'BTCUSDT',  full: 'Bitcoin / Tether USD',           type: 'crypto',   exchange: 'BINANCE',   logoImg: 'https://assets.coingecko.com/coins/images/1/small/bitcoin.png',           logoBg: '#f59e0b', isPositive: false },
    { symbol: 'BINANCE:ETHUSDT', name: 'ETHUSDT',  full: 'Ethereum / Tether USD',          type: 'crypto',   exchange: 'BINANCE',   logoImg: 'https://assets.coingecko.com/coins/images/279/small/ethereum.png',         logoBg: '#6366f1', isPositive: true },
    { symbol: 'BINANCE:BNBUSDT', name: 'BNBUSDT',  full: 'BNB / Tether USD',               type: 'crypto',   exchange: 'BINANCE',   logoImg: 'https://assets.coingecko.com/coins/images/825/small/bnb-icon2_2x.png',    logoBg: '#ca8a04', isPositive: true },
    { symbol: 'BINANCE:SOLUSDT', name: 'SOLUSDT',  full: 'Solana / Tether USD',            type: 'crypto',   exchange: 'BINANCE',   logoImg: 'https://assets.coingecko.com/coins/images/4128/small/solana.png',          logoBg: '#8b5cf6', isPositive: true },
    { symbol: 'BINANCE:XRPUSDT', name: 'XRPUSDT',  full: 'XRP / Tether USD',               type: 'crypto',   exchange: 'BINANCE',   logoImg: 'https://assets.coingecko.com/coins/images/44/small/xrp-symbol-white-128.png', logoBg: '#0ea5e9', isPositive: false },
    { symbol: 'BINANCE:ADAUSDT', name: 'ADAUSDT',  full: 'Cardano / Tether USD',           type: 'crypto',   exchange: 'BINANCE',   logoImg: 'https://assets.coingecko.com/coins/images/975/small/cardano.png',          logoBg: '#3b82f6', isPositive: false },
    { symbol: 'BINANCE:DOGEUSDT',name: 'DOGEUSDT', full: 'Dogecoin / Tether USD',          type: 'crypto',   exchange: 'BINANCE',   logoImg: 'https://assets.coingecko.com/coins/images/5/small/dogecoin.png',           logoBg: '#eab308', isPositive: true },
    // Indices
    { symbol: 'OANDA:NAS100USD', name: 'NAS100',   full: 'US Tech 100 Index (NASDAQ)',     type: 'index',    exchange: 'OANDA',     logoImg: 'https://flagcdn.com/h24/us.png',  logoBg: '#0891b2', isPositive: false },
    { symbol: 'OANDA:SPX500USD', name: 'SPX500',   full: 'S&P 500 Index',                  type: 'index',    exchange: 'OANDA',     logoImg: 'https://flagcdn.com/h24/us.png',  logoBg: '#16a34a', isPositive: true },
    { symbol: 'NSE:NIFTY50',     name: 'NIFTY 50', full: 'NIFTY 50 Index (NSE)',            type: 'index',    exchange: 'NSE',       logoImg: 'https://flagcdn.com/h24/in.png',  logoBg: '#ff9933', isPositive: true },
    { symbol: 'BSE:SENSEX',      name: 'SENSEX',   full: 'S&P BSE SENSEX Index',           type: 'index',    exchange: 'BSE',       logoImg: 'https://flagcdn.com/h24/in.png',  logoBg: '#ff9933', isPositive: true },
    { symbol: 'NSE:BANKNIFTY',   name: 'BANKNIFTY',full: 'NIFTY Bank Index (NSE)',         type: 'index',    exchange: 'NSE',       logoImg: 'https://flagcdn.com/h24/in.png',  logoBg: '#138808', isPositive: true },
    { symbol: 'OANDA:UK100GBP',  name: 'UK100',    full: 'UK 100 Index (FTSE)',             type: 'index',    exchange: 'OANDA',     logoImg: 'https://flagcdn.com/h24/gb.png',  logoBg: '#1d4ed8', isPositive: false },
    { symbol: 'OANDA:DE30EUR',   name: 'DAX30',    full: 'Germany 30 Index (DAX)',          type: 'index',    exchange: 'OANDA',     logoImg: 'https://flagcdn.com/h24/de.png',  logoBg: '#b45309', isPositive: true },
    // Commodities
    { symbol: 'OANDA:XAUUSD',    name: 'XAUUSD',   full: 'Gold Spot / U.S. Dollar',        type: 'commodity',exchange: 'OANDA',     logoImg: 'https://assets.coingecko.com/coins/images/32324/small/gold.png',          logoBg: '#d97706', isPositive: true },
    { symbol: 'OANDA:XAGUSD',    name: 'XAGUSD',   full: 'Silver Spot / U.S. Dollar',      type: 'commodity',exchange: 'OANDA',     logoImg: null,                                                                       logoBg: '#94a3b8', isPositive: false, logoText: 'Ag' },
    { symbol: 'NYMEX:CL1!',      name: 'CRUDE',    full: 'Crude Oil WTI Futures',           type: 'futures',  exchange: 'NYMEX',     logoImg: null,                                                                       logoBg: '#57534e', isPositive: false, logoText: 'OIL' },
    { symbol: 'CAPITALCOM:DXY',  name: 'DXY',      full: 'U.S. Dollar Index',               type: 'index',    exchange: 'CAPITALCOM',logoImg: 'https://flagcdn.com/h24/us.png',  logoBg: '#059669', isPositive: false },
    // Indian Stocks (NSE) — TradingView style dual badges (company logo + Indian flag)
    { symbol: 'NSE:NIFTY50',     name: 'NIFTY 50', full: 'NIFTY 50 Index (NSE)',            type: 'index',    exchange: 'NSE',       logoImg: 'https://flagcdn.com/h24/in.png',  logoBg: '#ff9933', isPositive: true },
    { symbol: 'BSE:SENSEX',      name: 'SENSEX',   full: 'S&P BSE SENSEX Index',           type: 'index',    exchange: 'BSE',       logoImg: 'https://flagcdn.com/h24/in.png',  logoBg: '#ff9933', isPositive: true },
    { symbol: 'NSE:BANKNIFTY',   name: 'BANKNIFTY',full: 'NIFTY Bank Index (NSE)',         type: 'index',    exchange: 'NSE',       logoImg: 'https://flagcdn.com/h24/in.png',  logoBg: '#138808', isPositive: true },
    { symbol: 'NSE:RELIANCE',   name: 'RELIANCE',  full: 'Reliance Industries Ltd.',       type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=ril.com&sz=64',           logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#1d4ed8', isPositive: true },
    { symbol: 'NSE:TCS',        name: 'TCS',       full: 'Tata Consultancy Services Ltd.', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=tcs.com&sz=64',           logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#2563eb', isPositive: true },
    { symbol: 'NSE:HDFCBANK',   name: 'HDFCBANK',  full: 'HDFC Bank Ltd.',                 type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=hdfcbank.com&sz=64',      logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#1e40af', isPositive: true },
    { symbol: 'NSE:INFY',       name: 'INFY',      full: 'Infosys Ltd.',                   type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=infosys.com&sz=64',       logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#0284c7', isPositive: true },
    { symbol: 'NSE:SBIN',       name: 'SBIN',      full: 'State Bank of India',            type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=sbi.co.in&sz=64',         logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#0369a1', isPositive: true },
    { symbol: 'NSE:ICICIBANK',  name: 'ICICIBANK', full: 'ICICI Bank Ltd.',                type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=icicibank.com&sz=64',      logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#b91c1c', isPositive: true },
    { symbol: 'NSE:TATAMOTORS', name: 'TATAMOTORS',full: 'Tata Motors Ltd.',               type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=tatamotors.com&sz=64',   logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#1e40af', isPositive: true },
    { symbol: 'NSE:ZOMATO',     name: 'ZOMATO',    full: 'Zomato Ltd.',                    type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=zomato.com&sz=64',       logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#e11d48', isPositive: true },
    { symbol: 'NSE:PAYTM',      name: 'PAYTM',     full: 'One97 Communications (Paytm)',   type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=paytm.com&sz=64',        logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#0284c7', isPositive: true },
    { symbol: 'NSE:BHARTIARTL', name: 'BHARTIARTL',full: 'Bharti Airtel Ltd.',             type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=airtel.in&sz=64',       logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#dc2626', isPositive: true },
    { symbol: 'NSE:TATASTEEL',  name: 'TATASTEEL', full: 'Tata Steel Ltd.',                type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=tatasteel.com&sz=64',    logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#2563eb', isPositive: true },
    { symbol: 'NSE:TITAN',      name: 'TITAN',     full: 'Titan Company Ltd.',             type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=titancompany.in&sz=64',  logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#d97706', isPositive: true },
    { symbol: 'NSE:JIOFIN',     name: 'JIOFIN',    full: 'Jio Financial Services Ltd.',    type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=jio.com&sz=64',          logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#1d4ed8', isPositive: true },
    { symbol: 'NSE:HAL',        name: 'HAL',       full: 'Hindustan Aeronautics Ltd.',     type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=hal-india.co.in&sz=64', logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#047857', isPositive: true },
    { symbol: 'NSE:BEL',        name: 'BEL',       full: 'Bharat Electronics Ltd.',        type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=bel-india.in&sz=64',    logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#0369a1', isPositive: true },
    { symbol: 'NSE:SWIGGY',     name: 'SWIGGY',    full: 'Swiggy Ltd.',                    type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=swiggy.com&sz=64',       logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#f97316', isPositive: true },
    { symbol: 'NSE:IRFC',       name: 'IRFC',      full: 'Indian Railway Finance Corp.',   type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=irfc.co.in&sz=64',       logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#1e40af', isPositive: true },
    { symbol: 'NSE:MARUTI',     name: 'MARUTI',    full: 'Maruti Suzuki India Ltd.',       type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=marutisuzuki.com&sz=64', logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#047857', isPositive: true },
    { symbol: 'NSE:WIPRO',      name: 'WIPRO',     full: 'Wipro Ltd.',                     type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=wipro.com&sz=64',         logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#6d28d9', isPositive: true },
    { symbol: 'NSE:ADANIENT',   name: 'ADANIENT',  full: 'Adani Enterprises Ltd.',         type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=adani.com&sz=64',         logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#b45309', isPositive: true },
    { symbol: 'NSE:BAJFINANCE', name: 'BAJFINANCE',full: 'Bajaj Finance Ltd.',             type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=bajajfinserv.in&sz=64',  logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#1e3a8a', isPositive: true },
    { symbol: 'NSE:HINDUNILVR', name: 'HINDUNILVR',full: 'Hindustan Unilever Ltd.',        type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=hul.co.in&sz=64',        logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#15803d', isPositive: true },
    { symbol: 'NSE:ASIANPAINT', name: 'ASIANPAINT',full: 'Asian Paints Ltd.',              type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=asianpaints.com&sz=64',  logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#c2410c', isPositive: true },
    { symbol: 'NSE:SUNPHARMA',  name: 'SUNPHARMA', full: 'Sun Pharmaceutical Inds.',       type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=sunpharma.com&sz=64',    logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#7e22ce', isPositive: true },
    { symbol: 'NSE:ITC',        name: 'ITC',       full: 'ITC Ltd.',                       type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=itcportal.com&sz=64',    logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#15803d', isPositive: true },
    { symbol: 'NSE:ONGC',       name: 'ONGC',      full: 'Oil & Natural Gas Corp.',        type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=ongcindia.com&sz=64',   logoImg2: 'https://flagcdn.com/h24/in.png', logoBg: '#b45309', isPositive: true },

    // Global Stocks
    { symbol: 'NASDAQ:AAPL',  name: 'AAPL',  full: 'Apple Inc.',                           type: 'stock',    exchange: 'NASDAQ',    logoImg: 'https://logo.clearbit.com/apple.com',           logoBg: '#475569', isPositive: true },
    { symbol: 'NASDAQ:TSLA',  name: 'TSLA',  full: 'Tesla Inc.',                            type: 'stock',    exchange: 'NASDAQ',    logoImg: 'https://logo.clearbit.com/tesla.com',           logoBg: '#dc2626', isPositive: true },
    { symbol: 'NASDAQ:NVDA',  name: 'NVDA',  full: 'NVIDIA Corporation',                    type: 'stock',    exchange: 'NASDAQ',    logoImg: 'https://logo.clearbit.com/nvidia.com',          logoBg: '#15803d', isPositive: true },
    { symbol: 'NASDAQ:META',  name: 'META',  full: 'Meta Platforms Inc.',                   type: 'stock',    exchange: 'NASDAQ',    logoImg: 'https://logo.clearbit.com/meta.com',            logoBg: '#2563eb', isPositive: false },
    { symbol: 'NASDAQ:AMZN',  name: 'AMZN',  full: 'Amazon.com Inc.',                      type: 'stock',    exchange: 'NASDAQ',    logoImg: 'https://logo.clearbit.com/amazon.com',          logoBg: '#d97706', isPositive: true },
    { symbol: 'NASDAQ:MSFT',  name: 'MSFT',  full: 'Microsoft Corporation',                type: 'stock',    exchange: 'NASDAQ',    logoImg: 'https://logo.clearbit.com/microsoft.com',       logoBg: '#0284c7', isPositive: true },
    { symbol: 'NASDAQ:GOOGL', name: 'GOOGL', full: 'Alphabet Inc. (Google)',                type: 'stock',    exchange: 'NASDAQ',    logoImg: 'https://logo.clearbit.com/google.com',          logoBg: '#ca8a04', isPositive: false },
    { symbol: 'NYSE:JPM',     name: 'JPM',   full: 'JPMorgan Chase & Co.',                 type: 'stock',    exchange: 'NYSE',      logoImg: 'https://logo.clearbit.com/jpmorganchase.com',   logoBg: '#1e40af', isPositive: true },
    { symbol: 'NYSE:GS',      name: 'GS',    full: 'Goldman Sachs Group Inc.',              type: 'stock',    exchange: 'NYSE',      logoImg: 'https://logo.clearbit.com/goldmansachs.com',    logoBg: '#3730a3', isPositive: false },
    { symbol: 'NYSE:V',       name: 'V',     full: 'Visa Inc.',                             type: 'stock',    exchange: 'NYSE',      logoImg: 'https://logo.clearbit.com/visa.com',            logoBg: '#1d4ed8', isPositive: true },
];

const CATEGORY_FILTERS = [
    { id: 'all',       label: 'All' },
    { id: 'stock',     label: 'Stocks' },
    { id: 'forex',     label: 'Forex' },
    { id: 'crypto',    label: 'Crypto' },
    { id: 'index',     label: 'Indices' },
    { id: 'futures',   label: 'Futures' },
    { id: 'commodity', label: 'Commodities' },
];

const DEFAULT_WATCHLIST_ITEMS = [
    { symbol: 'CAPITALCOM:DXY',  name: 'DXY',    full: 'U.S. Dollar Index',            price: '101.148',  change: '-0.045', changePct: '-0.04%', logoImg: 'https://flagcdn.com/h24/us.png',  logoBg: '#059669', isPositive: false },
    { symbol: 'OANDA:XAUUSD',   name: 'XAUUSD', full: 'Gold Spot / U.S. Dollar',      price: '4,161.21', change: '+41.71', changePct: '+1.02%', logoImg: 'https://assets.coingecko.com/coins/images/32324/small/gold.png', logoBg: '#d97706', isPositive: true,  flagged: true },
    { symbol: 'FX:USDCHF',      name: 'USDCHF', full: 'USD / Swiss Franc',            price: '0.81257',  change: '-0.000', changePct: '-0.04%', logoImg: 'https://flagcdn.com/h24/us.png',  logoBg: '#2563eb', isPositive: false },
    { symbol: 'FX:USDCAD',      name: 'USDCAD', full: 'USD / Canadian Dollar',        price: '1.40968',  change: '-0.001', changePct: '-0.09%', logoImg: 'https://flagcdn.com/h24/us.png',  logoBg: '#dc2626', isPositive: false },
    { symbol: 'FX:EURAUD',      name: 'EURAUD', full: 'EUR / Australian Dollar',      price: '1.63063',  change: '+0.002', changePct: '+0.12%', logoImg: 'https://flagcdn.com/h24/eu.png',  logoBg: '#089981', isPositive: true  },
    { symbol: 'OANDA:NAS100USD',name: 'NASDAQ', full: 'US Tech 100 Index',           price: '29,161.9', change: '+51.80', changePct: '+0.18%', logoImg: 'https://flagcdn.com/h24/us.png',  logoBg: '#0891b2', isPositive: true, flagged: true },
    { symbol: 'FX:EURUSD',      name: 'EURUSD', full: 'EUR / U.S. Dollar',           price: '1.14057',  change: '+0.001', changePct: '+0.07%', logoImg: 'https://flagcdn.com/h24/eu.png',  logoBg: '#089981', isPositive: true  },
    { symbol: 'FX:GBPUSD',      name: 'GBPUSD', full: 'GBP / U.S. Dollar',           price: '1.33704',  change: '-0.000', changePct: '-0.04%', logoImg: 'https://flagcdn.com/h24/gb.png',  logoBg: '#1e54e4', isPositive: false },
    { symbol: 'FX:NZDUSD',      name: 'NZDUSD', full: 'NZD / U.S. Dollar',           price: '0.58174',  change: '-0.001', changePct: '-0.17%', logoImg: 'https://flagcdn.com/h24/nz.png',  logoBg: '#f23645', isPositive: false },
    { symbol: 'BINANCE:BTCUSDT',name: 'BTCUSD', full: 'Bitcoin / Tether',             price: '66,066.0', change: '+179.0', changePct: '+0.27%', logoImg: 'https://assets.coingecko.com/coins/images/1/small/bitcoin.png', logoBg: '#f59e0b', isPositive: true, flagged: true },
    { symbol: 'FX:GBPJPY',      name: 'GBPJPY', full: 'GBP / Japanese Yen',          price: '217.969',  change: '-0.311', changePct: '-0.14%', logoImg: 'https://flagcdn.com/h24/gb.png',  logoBg: '#b91c1c', isPositive: false },
];

// ─── SymbolLogo: dual-flag for pairs (exactly like TradingView), single for others ───
// For pairs with logoImg2: renders two overlapping circles (base left, quote right-bottom)
function FlagCircle({ src, fallback, bg, px }) {
    const [err, setErr] = React.useState(false);
    return (
        <div
            className="rounded-full overflow-hidden flex items-center justify-center"
            style={{ width: px, height: px, background: bg || '#2962ff', flexShrink: 0, border: '1.5px solid #131722' }}
        >
            {src && !err
                ? <img src={src} alt="" className="w-full h-full object-cover" onError={() => setErr(true)} />
                : <span style={{ fontSize: px * 0.38, fontWeight: 700, color: '#fff' }}>{fallback}</span>
            }
        </div>
    );
}

const DEFAULT_INDIAN_WATCHLIST = [
    { symbol: 'NSE:NIFTY50',     name: 'NIFTY 50', full: 'NIFTY 50 Index (NSE)',            price: '23,974.76', change: '-197.80', changePct: '-0.82%', type: 'index',    exchange: 'NSE',       logoImg: 'https://www.niftyindices.com/favicon.ico',  logoBg: '#ff9933', isPositive: false, flagged: true },
    { symbol: 'BSE:SENSEX',      name: 'SENSEX',   full: 'S&P BSE SENSEX Index',           price: '76,730.40', change: '-714.70', changePct: '-0.92%', type: 'index',    exchange: 'BSE',       logoImg: 'https://www.bseindia.com/favicon.ico',  logoBg: '#ff9933', isPositive: false },
    { symbol: 'NSE:BANKNIFTY',   name: 'BANKNIFTY',full: 'NIFTY Bank Index (NSE)',         price: '57,137.60', change: '-680.00', changePct: '-1.19%', type: 'index',    exchange: 'NSE',       logoImg: 'https://www.niftyindices.com/favicon.ico',  logoBg: '#138808', isPositive: false, flagged: true },
    { symbol: 'NSE:RELIANCE',   name: 'RELIANCE',  full: 'Reliance Industries Ltd.',       price: '1,287.83', change: '-15.75', changePct: '-1.21%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=ril.com&sz=64',           logoBg: '#1d4ed8', isPositive: false },
    { symbol: 'NSE:TCS',        name: 'TCS',       full: 'Tata Consultancy Services Ltd.', price: '2,208.20', change: '-11.80', changePct: '-0.53%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=tcs.com&sz=64',           logoBg: '#2563eb', isPositive: false },
    { symbol: 'NSE:HDFCBANK',   name: 'HDFCBANK',  full: 'HDFC Bank Ltd.',                 price: '753.18', change: '-8.35', changePct: '-1.10%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=hdfcbank.com&sz=64',      logoBg: '#1e40af', isPositive: false, flagged: true },
    { symbol: 'NSE:INFY',       name: 'INFY',      full: 'Infosys Ltd.',                   price: '1,052.85', change: '-18.55', changePct: '-1.73%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=infosys.com&sz=64',       logoBg: '#0284c7', isPositive: false },
    { symbol: 'NSE:SBIN',       name: 'SBIN',      full: 'State Bank of India',            price: '1,024.78', change: '-19.00', changePct: '-1.82%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=sbi.co.in&sz=64',         logoBg: '#0369a1', isPositive: false },
    { symbol: 'NSE:ICICIBANK',  name: 'ICICIBANK', full: 'ICICI Bank Ltd.',                price: '1,439.72', change: '-22.40', changePct: '-1.53%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=icicibank.com&sz=64',      logoBg: '#b91c1c', isPositive: false },
    { symbol: 'NSE:MARUTI',     name: 'MARUTI',    full: 'Maruti Suzuki India Ltd.',       price: '13,549.45', change: '-95.55', changePct: '-0.70%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=marutisuzuki.com&sz=64', logoBg: '#047857', isPositive: false },
    { symbol: 'NSE:WIPRO',      name: 'WIPRO',     full: 'Wipro Ltd.',                     price: '174.29', change: '-0.45', changePct: '-0.26%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=wipro.com&sz=64',         logoBg: '#6d28d9', isPositive: false },
    { symbol: 'NSE:ADANIENT',   name: 'ADANIENT',  full: 'Adani Enterprises Ltd.',         price: '3,146.22', change: '-35.00', changePct: '-1.10%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=adani.com&sz=64',         logoBg: '#b45309', isPositive: false },
    { symbol: 'NSE:BAJFINANCE', name: 'BAJFINANCE',full: 'Bajaj Finance Ltd.',             price: '1,060.69', change: '-8.90', changePct: '-0.83%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=bajajfinserv.in&sz=64',  logoBg: '#1e3a8a', isPositive: false },
    { symbol: 'NSE:HINDUNILVR', name: 'HINDUNILVR',full: 'Hindustan Unilever Ltd.',        price: '2,155.64', change: '+12.00', changePct: '+0.56%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=hul.co.in&sz=64',        logoBg: '#15803d', isPositive: true },
    { symbol: 'NSE:ASIANPAINT', name: 'ASIANPAINT',full: 'Asian Paints Ltd.',              price: '2,693.54', change: '-4.30', changePct: '-0.16%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=asianpaints.com&sz=64',  logoBg: '#c2410c', isPositive: false },
    { symbol: 'NSE:SUNPHARMA',  name: 'SUNPHARMA', full: 'Sun Pharmaceutical Inds.',       price: '1,942.85', change: '-18.80', changePct: '-0.96%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=sunpharma.com&sz=64',    logoBg: '#7e22ce', isPositive: false },
    { symbol: 'NSE:ITC',        name: 'ITC',       full: 'ITC Ltd.',                       price: '280.88', change: '-0.30', changePct: '-0.11%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=itcportal.com&sz=64',    logoBg: '#15803d', isPositive: false },
    { symbol: 'NSE:ONGC',       name: 'ONGC',      full: 'Oil & Natural Gas Corp.',        price: '252.03', change: '+2.15', changePct: '+0.86%', type: 'stock',    exchange: 'NSE',       logoImg: 'https://www.google.com/s2/favicons?domain=ongcindia.com&sz=64',   logoBg: '#b45309', isPositive: true },
];

function SymbolLogo({ item, size = 'sm' }) {
    const px = size === 'sm' ? 24 : 32;
    const fallback = item.logoText || (item.name ? item.name.charAt(0) : '?');

    return (
        <div
            className="rounded-full overflow-hidden flex items-center justify-center shrink-0 border border-white/10 shadow-sm"
            style={{ width: px, height: px, background: item.logoBg || '#2962ff' }}
        >
            <FlagCircle src={item.logoImg} fallback={fallback} bg={item.logoBg} px={px} />
        </div>
    );
}
export default function CustomWatchlist({ currentSymbol, onSelectSymbol }) {
    const [sectionOpen, setSectionOpen] = useState(true);
    const [liveData, setLiveData] = useState({});
    const [showAddModal, setShowAddModal] = useState(false);

    // Multi-Watchlist state: 'indian' | 'main' | 'forex' | 'crypto' | custom name
    const [activeWatchlistId, setActiveWatchlistId] = useState(() => {
        try { return localStorage.getItem('friday_active_watchlist') || 'indian'; } catch(_) { return 'indian'; }
    });
    const [showWatchlistDropdown, setShowWatchlistDropdown] = useState(false);
    const [showCreateWatchlistModal, setShowCreateWatchlistModal] = useState(false);
    const [newWatchlistNameInput, setNewWatchlistNameInput] = useState('');
    const [customWatchlists, setCustomWatchlists] = useState(() => {
        try { return JSON.parse(localStorage.getItem('friday_custom_watchlists') || '[]'); } catch(_) { return []; }
    });

    // ── Watchlist: load based on active list + permanent storage ─────
    const [watchlistItems, setWatchlistItems] = useState(() => {
        try {
            const stored = localStorage.getItem(`friday_watchlist_items_${activeWatchlistId}`);
            if (stored !== null) {
                const parsed = JSON.parse(stored);
                if (Array.isArray(parsed)) {
                    return parsed.map(item => {
                        if (item.symbol === 'OANDA:XAUUSD' && (item.price === '4,119.03' || item.price === '4,161.21')) {
                            return { ...item, price: '4,163.74' };
                        }
                        return item;
                    });
                }
            }
        } catch (_) {}
        const defaults = activeWatchlistId === 'indian' ? DEFAULT_INDIAN_WATCHLIST : DEFAULT_WATCHLIST_ITEMS;
        try { localStorage.setItem(`friday_watchlist_items_${activeWatchlistId}`, JSON.stringify(defaults)); } catch(_) {}
        return defaults;
    });
    // ── Resizable Watchlist Width state (draggable left/right) ─────────────────
    const [watchlistWidth, setWatchlistWidth] = useState(() => {
        try { return parseInt(localStorage.getItem('friday_watchlist_width') || '300', 10); } catch (_) { return 300; }
    });
    const isResizingRef = useRef(false);

    const handleMouseDownResize = React.useCallback((e) => {
        e.preventDefault();
        isResizingRef.current = true;
        const startX = e.clientX;
        const startWidth = watchlistWidth;

        const onMouseMove = (moveEvent) => {
            if (!isResizingRef.current) return;
            const deltaX = startX - moveEvent.clientX; // Left drag increases width
            const newWidth = Math.max(180, Math.min(550, startWidth + deltaX));
            setWatchlistWidth(newWidth);
            try { localStorage.setItem('friday_watchlist_width', String(newWidth)); } catch (_) {}
        };

        const onMouseUp = () => {
            isResizingRef.current = false;
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };

        window.addEventListener('mousemove', onMouseMove);
        window.addEventListener('mouseup', onMouseUp);
    }, [watchlistWidth]);

    const [apiLoading, setApiLoading] = useState(false);
    const [draggedIndex, setDraggedIndex] = useState(null);

    // Persistent state helper (writes to current watchlist storage key)
    const saveWatchlist = (newItems) => {
        setWatchlistItems(newItems);
        try {
            localStorage.setItem(`friday_watchlist_items_${activeWatchlistId}`, JSON.stringify(newItems));
        } catch (_) {}
    };

    // Switch watchlist handler
    const selectWatchlist = (id, defaultItems) => {
        setActiveWatchlistId(id);
        setShowWatchlistDropdown(false);
        try { localStorage.setItem('friday_active_watchlist', id); } catch(_) {}
        try {
            const stored = localStorage.getItem(`friday_watchlist_items_${id}`);
            if (stored !== null) {
                setWatchlistItems(JSON.parse(stored));
                return;
            }
        } catch(_) {}
        setWatchlistItems(defaultItems);
        try { localStorage.setItem(`friday_watchlist_items_${id}`, JSON.stringify(defaultItems)); } catch(_) {}
    };

    const handleCreateCustomWatchlist = (e) => {
        e.preventDefault();
        const name = newWatchlistNameInput.trim();
        if (!name) return;
        const newWl = { id: `custom_${Date.now()}`, name, items: DEFAULT_INDIAN_WATCHLIST.slice(0, 4) };
        const updated = [...customWatchlists, newWl];
        setCustomWatchlists(updated);
        try { localStorage.setItem('friday_custom_watchlists', JSON.stringify(updated)); } catch(_) {}
        selectWatchlist(newWl.id, newWl.items);
        setNewWatchlistNameInput('');
        setShowCreateWatchlistModal(false);
    };

    // Drag and Drop handlers
    const handleDragStart = (e, index) => {
        setDraggedIndex(index);
        e.dataTransfer.effectAllowed = 'move';
    };

    const handleDragOver = (e, index) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    };

    const handleDrop = (e, targetIndex) => {
        e.preventDefault();
        if (draggedIndex === null || draggedIndex === targetIndex) return;

        const updated = [...watchlistItems];
        const [movedItem] = updated.splice(draggedIndex, 1);
        updated.splice(targetIndex, 0, movedItem);
        saveWatchlist(updated);
        setDraggedIndex(null);
    };

    // ── Add a symbol: POST to API + optimistic UI update ─────────────────────
    const handleAddFromResult = async (dbItem) => {
        if (inWatchlist.has(dbItem.symbol)) return;
        const newItem = { ...dbItem, price: dbItem.price || '—', change: dbItem.change || '—', changePct: dbItem.changePct || '—', flagged: false };
        const updated = [newItem, ...watchlistItems];
        saveWatchlist(updated);
        setShowAddModal(false);
        try {
            await fetch('http://localhost:8000/api/watchlist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    symbol:     dbItem.symbol,
                    name:       dbItem.name,
                    full:       dbItem.full || '',
                    logoImg:    dbItem.logoImg || '',
                    logoBg:     dbItem.logoBg || '#2962ff',
                    type:       dbItem.type || '',
                    exchange:   dbItem.exchange || '',
                    isPositive: dbItem.isPositive ?? true,
                    flagged:    dbItem.flagged ?? false,
                }),
            });
        } catch (_) { /* offline: optimistic state already applied */ }
    };

    // ── Delete: DELETE from API + optimistic UI update ────────────────────────
    const handleDeleteSymbol = async (symbolToDelete, e) => {
        e.stopPropagation();
        const updated = watchlistItems.filter(i => i.symbol !== symbolToDelete);
        saveWatchlist(updated);
        try {
            await fetch(`http://localhost:8000/api/watchlist/${encodeURIComponent(symbolToDelete)}`, {
                method: 'DELETE',
            });
        } catch (_) { /* offline: optimistic state already applied */ }
    };

    // ── Live price polling every 1.5s ─────────────────────────────────────────
    useEffect(() => {
        const fetchLivePrices = async () => {
            try {
                const res = await fetch('http://localhost:8000/api/trading/live-prices');
                if (res.ok) setLiveData(await res.json());
            } catch (_) {}
        };
        fetchLivePrices();
        const iv = setInterval(fetchLivePrices, 1500);
        return () => clearInterval(iv);
    }, []);

    // ── Sync live prices into watchlistItems & erase stale localStorage prices ────
    useEffect(() => {
        if (!liveData || Object.keys(liveData).length === 0) return;
        setWatchlistItems(prev => {
            let changed = false;
            const updated = prev.map(item => {
                const live = liveData[item.symbol];
                if (live && live.price_str && item.price !== live.price_str) {
                    changed = true;
                    return {
                        ...item,
                        price: live.price_str,
                        change: live.change_str || item.change,
                        changePct: live.pct_str || item.changePct,
                        isPositive: live.isPositive ?? item.isPositive
                    };
                }
                return item;
            });
            if (changed) {
                try { localStorage.setItem(`friday_watchlist_items_${activeWatchlistId}`, JSON.stringify(updated)); } catch(_) {}
            }
            return changed ? updated : prev;
        });
    }, [liveData, activeWatchlistId]);

    // ── Search modal state ────────────────────────────────────────────────────
    const [searchQuery, setSearchQuery] = useState('');
    const [activeCategory, setActiveCategory] = useState('all');
    const [remoteResults, setRemoteResults] = useState([]);
    const [isSearchingRemote, setIsSearchingRemote] = useState(false);
    const searchInputRef = useRef(null);

    useEffect(() => {
        if (showAddModal) {
            setSearchQuery('');
            setActiveCategory('all');
            setRemoteResults([]);
            setTimeout(() => searchInputRef.current?.focus(), 50);
        }
    }, [showAddModal]);

    // Live remote search across ALL 5000+ global stocks via Yahoo Finance API
    useEffect(() => {
        const q = searchQuery.trim();
        if (!q) {
            setRemoteResults([]);
            return;
        }
        const timer = setTimeout(async () => {
            setIsSearchingRemote(true);
            try {
                const res = await fetch(`http://localhost:8000/api/trading/search?q=${encodeURIComponent(q)}`);
                if (res.ok) {
                    const data = await res.json();
                    setRemoteResults(data.results || []);
                }
            } catch (_) {}
            setIsSearchingRemote(false);
        }, 200);
        return () => clearTimeout(timer);
    }, [searchQuery]);

    // Combine preset SYMBOL_DATABASE with live remote search results (deduped)
    const localMatches = SYMBOL_DATABASE.filter(s => {
        const q = searchQuery.trim().toLowerCase();
        const matchesSearch = !q || s.name.toLowerCase().includes(q) || s.full.toLowerCase().includes(q) || s.symbol.toLowerCase().includes(q);
        const matchesCategory = activeCategory === 'all' || s.type === activeCategory;
        return matchesSearch && matchesCategory;
    });

    const seenSymbols = new Set(localMatches.map(m => m.symbol));
    const dedupedRemote = remoteResults.filter(r => !seenSymbols.has(r.symbol) && (activeCategory === 'all' || r.type === activeCategory));
    const searchResults = [...localMatches, ...dedupedRemote];

    const inWatchlist = new Set(watchlistItems.map(i => i.symbol));

    const activeItem = watchlistItems.find(i => i.symbol === currentSymbol) || watchlistItems[0] || DEFAULT_WATCHLIST_ITEMS[0];

    return (
        <div className="flex h-full select-none font-sans z-30 shadow-2xl overflow-hidden bg-[#131722] text-[#d1d4dc]">
            {/* Draggable Resize Divider Handle on Left Edge */}
            <div
                onMouseDown={handleMouseDownResize}
                className="w-2 hover:w-2.5 h-full bg-[#2a2e39]/60 hover:bg-[#2962ff] active:bg-[#2962ff] cursor-col-resize transition-all shrink-0 z-50 flex items-center justify-center group"
                title="Drag left/right to resize watchlist width"
            >
                <div className="w-0.5 h-10 bg-slate-500/50 group-hover:bg-white rounded-full transition-colors" />
            </div>

            {/* Main Watchlist Container (Dynamic Resizable Width) */}
            <div
                style={{ width: `${watchlistWidth}px` }}
                className="flex flex-col h-full bg-[#131722] border-l border-[#2a2e39] py-1 shrink-0 transition-none overflow-hidden"
            >
                {/* Watchlist Header Tabs / Dropdown Options */}
                <div className="h-13 border-b border-[#2a2e39] px-3 flex items-center justify-between bg-[#131722] relative z-40">
                    <div 
                        onClick={() => setShowWatchlistDropdown(s => !s)}
                        className="flex items-center gap-2 cursor-pointer hover:text-white group relative"
                    >
                        <span className="text-sm font-black tracking-wide uppercase text-slate-100 group-hover:text-cyan-400 transition-colors">
                            {activeWatchlistId === 'indian' ? 'Indian Stocks' : activeWatchlistId === 'main' ? 'Main Watchlist' : (customWatchlists.find(w => w.id === activeWatchlistId)?.name || 'Watchlist')} ({watchlistItems.length})
                        </span>
                        <ChevronDown size={16} className="text-slate-400 group-hover:text-cyan-400 transition-colors" />

                        {/* Watchlist Switcher Dropdown */}
                        <AnimatePresence>
                            {showWatchlistDropdown && (
                                <motion.div
                                    initial={{ opacity: 0, y: 6, scale: 0.96 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    exit={{ opacity: 0, y: 4, scale: 0.96 }}
                                    className="absolute left-0 top-10 w-64 rounded-xl bg-[#1e222d] border border-[#2a2e39] shadow-2xl p-2 z-50 flex flex-col gap-1 text-xs"
                                    onClick={e => e.stopPropagation()}
                                >
                                    <div className="px-2 py-1 text-[11px] font-bold text-slate-400 uppercase font-mono tracking-wider">
                                        Select Watchlist
                                    </div>
                                    <button
                                        onClick={() => selectWatchlist('indian', DEFAULT_INDIAN_WATCHLIST)}
                                        className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center justify-between font-semibold transition-all ${
                                            activeWatchlistId === 'indian' ? 'bg-[#2962ff]/20 text-cyan-400 font-bold border border-[#2962ff]/40' : 'hover:bg-white/5 text-slate-200'
                                        }`}
                                    >
                                        <span>Indian Stocks (NSE/BSE)</span>
                                        <span className="text-xs opacity-70 font-mono">{DEFAULT_INDIAN_WATCHLIST.length}</span>
                                    </button>
                                    <button
                                        onClick={() => selectWatchlist('main', DEFAULT_WATCHLIST_ITEMS)}
                                        className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center justify-between font-semibold transition-all ${
                                            activeWatchlistId === 'main' ? 'bg-[#2962ff]/20 text-cyan-400 font-bold border border-[#2962ff]/40' : 'hover:bg-white/5 text-slate-200'
                                        }`}
                                    >
                                        <span>Main Global Watchlist</span>
                                        <span className="text-xs opacity-70 font-mono">{DEFAULT_WATCHLIST_ITEMS.length}</span>
                                    </button>

                                    {customWatchlists.map(cw => (
                                        <button
                                            key={cw.id}
                                            onClick={() => selectWatchlist(cw.id, cw.items)}
                                            className={`w-full text-left px-3 py-2.5 rounded-lg flex items-center justify-between font-semibold transition-all ${
                                                activeWatchlistId === cw.id ? 'bg-[#2962ff]/20 text-cyan-400 font-bold border border-[#2962ff]/40' : 'hover:bg-white/5 text-slate-200'
                                            }`}
                                        >
                                            <span>📊 {cw.name}</span>
                                            <span className="text-xs opacity-70 font-mono">{cw.items?.length || 0}</span>
                                        </button>
                                    ))}

                                    <div className="h-px bg-[#2a2e39] my-1" />
                                    <button
                                        onClick={() => { setShowWatchlistDropdown(false); setShowCreateWatchlistModal(true); }}
                                        className="w-full text-left px-3 py-2.5 rounded-lg flex items-center gap-2 text-cyan-400 hover:bg-cyan-500/10 font-bold transition-all"
                                    >
                                        <Plus size={15} />
                                        <span>Create New Watchlist...</span>
                                    </button>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>

                    <div className="flex items-center gap-2">
                        {/* Add Symbol Plus Button */}
                        <button 
                            onClick={() => setShowAddModal(true)} 
                            className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-cyan-400 hover:text-cyan-300 transition-all cursor-pointer border border-white/10"
                            title="Add Symbol to Watchlist"
                        >
                            <Plus size={18} />
                        </button>
                    </div>
                </div>

                {/* Table Header Columns: Symbol | Last | Chg | Chg% */}
                <div className="grid grid-cols-12 px-4 py-2.5 text-xs font-mono font-bold text-slate-300 uppercase tracking-wider bg-[#131722] border-b border-[#2a2e39]">
                    <div className="col-span-4">Symbol</div>
                    <div className="col-span-3 text-right">Last</div>
                    <div className="col-span-2 text-right">Chg</div>
                    <div className="col-span-3 text-right">Chg%</div>
                </div>

                {/* Watchlist Items Scroll List */}
                <div className="flex-1 overflow-y-auto px-2 py-1.5 space-y-2 scrollbar-thin scrollbar-thumb-[#2a2e39]">
                    {/* Collapsible Section Header */}
                    <div 
                        onClick={() => setSectionOpen(!sectionOpen)} 
                        className="mx-1 px-4 py-2.5 flex items-center gap-2 text-xs font-mono font-bold text-cyan-400 uppercase bg-[#1e222d]/80 rounded-xl cursor-pointer hover:bg-[#1e222d] border border-cyan-500/20 shadow-sm"
                    >
                        {sectionOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        <span className="tracking-widest">SECTION 1</span>
                    </div>

                    {sectionOpen && watchlistItems.map((item, idx) => {
                        const isSelected = currentSymbol === item.symbol;
                        const isDragging = draggedIndex === idx;
                        const liveInfo = liveData[item.symbol];

                        // Use formatted live data if available, fall back to static DB values
                        const displayPrice  = liveInfo ? liveInfo.price_str  : (item.price   || '—');
                        const displayChange = liveInfo ? liveInfo.change_str : (item.change  || '—');
                        const displayPct    = liveInfo ? liveInfo.pct_str    : (item.changePct || '—');
                        const isPositive    = liveInfo ? liveInfo.isPositive : item.isPositive;
                        const tickDir       = liveInfo ? liveInfo.tick_direction : null;

                        return (
                            <div
                                key={item.symbol}
                                draggable={true}
                                onDragStart={(e) => handleDragStart(e, idx)}
                                onDragOver={(e) => handleDragOver(e, idx)}
                                onDrop={(e) => handleDrop(e, idx)}
                                onClick={() => onSelectSymbol(item.symbol)}
                                className={`group grid items-center px-3 py-2.5 rounded-xl cursor-grab active:cursor-grabbing transition-all relative border backdrop-blur-xl gap-1 ${
                                    watchlistWidth < 300 ? 'grid-cols-12' : 'grid-cols-12'
                                } ${
                                    isDragging ? 'opacity-30 border-cyan-400 border-dashed scale-95' :
                                    isSelected 
                                        ? 'bg-[#1e222d] border-[#2962ff] shadow-lg ring-1 ring-[#2962ff]/50' 
                                        : 'bg-white/[0.04] hover:bg-white/[0.09] border-white/5 hover:border-white/15'
                                }`}
                            >
                                {/* Left Red Bookmark Ribbon Flag */}
                                {item.flagged && (
                                    <div className="absolute left-0 top-2 bottom-2 w-1 rounded-r bg-[#f23645]" />
                                )}

                                {/* Column 1: SymbolLogo + Ticker Name */}
                                <div className={`${watchlistWidth < 300 ? 'col-span-5' : 'col-span-4'} flex items-center gap-2 min-w-0 pr-1`}>
                                    <SymbolLogo item={item} size="sm" />
                                    <span className="text-xs font-extrabold text-white font-mono truncate tracking-tight">
                                        {item.name}
                                    </span>
                                </div>

                                {/* Column 2: Last Price — blinks green/red on tick */}
                                <div className={`${watchlistWidth < 300 ? 'col-span-4' : 'col-span-3'} text-right font-mono text-xs font-bold transition-all ${
                                    tickDir === 'up' 
                                        ? 'text-[#089981] animate-pulse' 
                                        : tickDir === 'down' 
                                        ? 'text-[#f23645] animate-pulse' 
                                        : 'text-slate-100'
                                }`}>
                                    {displayPrice}
                                </div>

                                {/* Column 3: Change Absolute (Hidden when narrow) */}
                                {watchlistWidth >= 300 && (
                                    <div className={`col-span-2 text-right font-mono text-[11px] font-semibold ${
                                        isPositive ? 'text-[#089981]' : 'text-[#f23645]'
                                    }`}>
                                        {displayChange}
                                    </div>
                                )}

                                {/* Column 4: Change % / Delete Icon on Hover */}
                                <div className={`${watchlistWidth < 300 ? 'col-span-3' : 'col-span-3'} flex items-center justify-end font-mono text-[11px] font-bold relative pl-1`}>
                                    <span className={`group-hover:hidden ${isPositive ? 'text-[#089981]' : 'text-[#f23645]'}`}>
                                        {displayPct}
                                    </span>
                                    <button
                                        onClick={(e) => handleDeleteSymbol(item.symbol, e)}
                                        className="hidden group-hover:flex p-1 rounded-lg hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition-all"
                                        title={`Delete ${item.name}`}
                                    >
                                        <Trash2 size={13} />
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>

                {/* Bottom Active Symbol Toolbar Pane */}
                <div className="h-11 border-t border-[#2a2e39] px-3.5 flex items-center justify-between bg-[#131722]">
                    <div className="flex items-center gap-2 min-w-0">
                        <SymbolLogo item={activeItem || DEFAULT_INDIAN_WATCHLIST[0]} size="sm" />
                        <span className="font-bold text-white text-xs font-mono truncate">{activeItem?.name || 'TICKER'}</span>
                    </div>

                    <div className="flex items-center gap-3 text-slate-400 shrink-0">
                        <button className="hover:text-white transition-all cursor-pointer"><Grid size={14} /></button>
                        <button onClick={() => setShowAddModal(true)} className="hover:text-white transition-all cursor-pointer"><Plus size={14} /></button>
                    </div>
                </div>
            </div>

            {/* TradingView Rightmost Vertical Icon Bar */}
            <div className="w-[45px] bg-[#131722] border-l border-[#2a2e39] flex flex-col items-center justify-between py-3 text-slate-400 shrink-0">
                <div className="flex flex-col items-center gap-5">
                    <button className="p-2 rounded hover:bg-[#1e222d] text-[#2962ff] transition-all cursor-pointer" title="Watchlist and details">
                        <Clock size={18} />
                    </button>
                    <button className="p-2 rounded hover:bg-[#1e222d] hover:text-slate-200 transition-all cursor-pointer" title="Object tree">
                        <Layers size={18} />
                    </button>
                    <button className="p-2 rounded hover:bg-[#1e222d] hover:text-slate-200 transition-all cursor-pointer" title="Chats">
                        <MessageSquare size={18} />
                    </button>
                    <button className="p-2 rounded hover:bg-[#1e222d] hover:text-slate-200 transition-all cursor-pointer" title="Alerts">
                        <Bell size={18} />
                    </button>
                    <button className="p-2 rounded hover:bg-[#1e222d] hover:text-slate-200 transition-all cursor-pointer" title="Calendar">
                        <Calendar size={18} />
                    </button>
                    <button className="p-2 rounded hover:bg-[#1e222d] hover:text-slate-200 transition-all cursor-pointer" title="News headlines">
                        <Rss size={18} />
                    </button>
                </div>

                <div className="flex flex-col items-center gap-4">
                    <button className="p-2 rounded hover:bg-[#1e222d] hover:text-slate-200 transition-all cursor-pointer">
                        <Grid size={18} />
                    </button>
                    <button className="p-2 rounded hover:bg-[#1e222d] hover:text-slate-200 transition-all cursor-pointer">
                        <HelpCircle size={18} />
                    </button>
                </div>
            </div>

            {/* ══════════════════════════════════════════════════════════
                TradingView-style "Add symbol" Modal
                ══════════════════════════════════════════════════════════ */}
            <AnimatePresence>
                {showAddModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
                        onClick={() => setShowAddModal(false)}
                    >
                        <motion.div
                            initial={{ opacity: 0, y: -16, scale: 0.97 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -10, scale: 0.97 }}
                            transition={{ type: 'spring', stiffness: 440, damping: 30 }}
                            className="w-[540px] bg-[#1e222d] rounded-2xl border border-white/10 shadow-2xl flex flex-col overflow-hidden"
                            onClick={e => e.stopPropagation()}
                        >
                            {/* ── Title Bar ── */}
                            <div className="flex items-center justify-between px-5 pt-4 pb-3 border-b border-white/8">
                                <span className="text-sm font-semibold text-white tracking-tight">Add symbol</span>
                                <button
                                    onClick={() => setShowAddModal(false)}
                                    className="p-1 rounded-md hover:bg-white/10 text-slate-400 hover:text-white transition-all cursor-pointer"
                                >
                                    <X size={16} />
                                </button>
                            </div>

                            {/* ── Search Bar ── */}
                            <div className="px-4 pt-3 pb-2">
                                <div className="flex items-center gap-2.5 bg-[#131722] border border-white/10 rounded-lg px-3 py-2.5 focus-within:border-[#2962ff] focus-within:ring-1 focus-within:ring-[#2962ff]/30 transition-all">
                                    <Search size={15} className="text-slate-400 shrink-0" />
                                    <input
                                        ref={searchInputRef}
                                        type="text"
                                        value={searchQuery}
                                        onChange={e => setSearchQuery(e.target.value)}
                                        placeholder="Symbol, ISIN, or CUSIP"
                                        className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 outline-none font-sans"
                                    />
                                    {searchQuery && (
                                        <button onClick={() => setSearchQuery('')} className="text-slate-500 hover:text-slate-200 transition-all cursor-pointer shrink-0">
                                            <X size={14} />
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* ── Category Filter Pills ── */}
                            <div className="px-4 pb-2 flex items-center gap-1.5 flex-wrap">
                                {CATEGORY_FILTERS.map(cat => (
                                    <button
                                        key={cat.id}
                                        onClick={() => setActiveCategory(cat.id)}
                                        className={`px-3 py-1 rounded-full text-[11px] font-semibold transition-all cursor-pointer border ${
                                            activeCategory === cat.id
                                                ? 'bg-[#2962ff] text-white border-[#2962ff] shadow-sm'
                                                : 'bg-white/5 text-slate-400 border-white/10 hover:bg-white/10 hover:text-slate-200'
                                        }`}
                                    >
                                        {cat.label}
                                    </button>
                                ))}
                            </div>

                            {/* ── Results List ── */}
                            <div className="overflow-y-auto max-h-[340px] px-2 pb-3 scrollbar-thin scrollbar-thumb-[#2a2e39] scrollbar-track-transparent">
                                {searchQuery.trim() && (
                                    <div
                                        onClick={() => {
                                            const rawQ = searchQuery.trim().toUpperCase();
                                            const formattedSym = rawQ.includes(':') ? rawQ : `NSE:${rawQ}`;
                                            const customItem = {
                                                symbol: formattedSym,
                                                name: rawQ.replace(/^NSE:|^BSE:|^NASDAQ:|^NYSE:/, ''),
                                                full: `${rawQ} (Custom Symbol)`,
                                                type: 'stock',
                                                exchange: rawQ.includes(':') ? rawQ.split(':')[0] : 'NSE',
                                                logoImg: `https://www.google.com/s2/favicons?domain=${rawQ.toLowerCase()}.com&sz=64`,
                                                logoImg2: 'https://flagcdn.com/h24/in.png',
                                                logoBg: '#1d4ed8',
                                                price: '—', change: '—', changePct: '—',
                                                isPositive: true, flagged: false
                                            };
                                            handleAddFromResult(customItem);
                                        }}
                                        className="group mb-2 p-3 rounded-xl bg-[#2962ff]/15 hover:bg-[#2962ff]/30 border border-[#2962ff]/40 flex items-center justify-between cursor-pointer transition-all"
                                    >
                                        <div className="flex items-center gap-2.5">
                                            <div className="w-7 h-7 rounded-full bg-[#2962ff] text-white flex items-center justify-center font-bold">
                                                <Plus size={14} />
                                            </div>
                                            <div>
                                                <div className="text-xs font-bold text-cyan-300 font-mono">Add custom symbol "{searchQuery.toUpperCase()}"</div>
                                                <div className="text-[10px] text-slate-400 font-mono">Click to insert into your active Watchlist</div>
                                            </div>
                                        </div>
                                        <span className="text-[10px] font-bold font-mono px-2 py-1 rounded bg-[#2962ff] text-white">ADD SYMBOL</span>
                                    </div>
                                )}

                                {searchResults.length === 0 && !searchQuery.trim() ? (
                                    <div className="flex flex-col items-center justify-center py-12 text-slate-500">
                                        <Search size={28} className="mb-3 opacity-40" />
                                        <p className="text-xs">Type a symbol to search...</p>
                                    </div>
                                ) : (
                                    searchResults.map(item => {
                                        const alreadyAdded = inWatchlist.has(item.symbol);
                                        return (
                                            <div
                                                key={item.symbol}
                                                className="group flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/[0.06] transition-all cursor-pointer"
                                                onClick={() => { if (!alreadyAdded) { handleAddFromResult(item); setShowAddModal(false); } }}
                                            >
                                                {/* Logo Circle */}
                                                <SymbolLogo item={item} size="lg" />

                                                {/* Symbol + Full Name */}
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-1.5">
                                                        <span className="text-[13px] font-bold text-white font-mono leading-none">{item.name}</span>
                                                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide ${
                                                            item.type === 'crypto'    ? 'bg-amber-500/20 text-amber-400' :
                                                            item.type === 'forex'     ? 'bg-blue-500/20 text-blue-400' :
                                                            item.type === 'stock'     ? 'bg-slate-500/30 text-slate-300' :
                                                            item.type === 'index'     ? 'bg-cyan-500/20 text-cyan-400' :
                                                            item.type === 'futures'   ? 'bg-orange-500/20 text-orange-400' :
                                                                                        'bg-yellow-500/20 text-yellow-400'
                                                        }`}>
                                                            {item.type}
                                                        </span>
                                                        <span className="text-[9px] text-slate-500 font-mono uppercase">{item.exchange}</span>
                                                    </div>
                                                    <p className="text-[11px] text-slate-400 truncate mt-0.5 leading-none">{item.full}</p>
                                                </div>

                                                {/* Add / Already Added button */}
                                                <button
                                                    onClick={e => { e.stopPropagation(); if (!alreadyAdded) { handleAddFromResult(item); setShowAddModal(false); }}}
                                                    className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center transition-all cursor-pointer border ${
                                                        alreadyAdded
                                                            ? 'bg-[#089981]/20 border-[#089981]/40 text-[#089981] cursor-default'
                                                            : 'bg-white/5 border-white/10 text-slate-400 hover:bg-[#2962ff] hover:border-[#2962ff] hover:text-white group-hover:border-white/30 group-hover:text-white'
                                                    }`}
                                                    title={alreadyAdded ? 'Already in watchlist' : `Add ${item.name}`}
                                                >
                                                    {alreadyAdded ? (
                                                        <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
                                                    ) : (
                                                        <Plus size={13} />
                                                    )}
                                                </button>
                                            </div>
                                        );
                                    })
                                )}
                            </div>

                            {/* ── Footer Hint ── */}
                            <div className="px-5 py-2.5 border-t border-white/8 flex items-center gap-2 text-[10.5px] text-slate-500">
                                <kbd className="px-1.5 py-0.5 rounded bg-white/8 border border-white/10 text-[9px] font-mono text-slate-400">↑↓</kbd>
                                <span>Navigate</span>
                                <kbd className="px-1.5 py-0.5 rounded bg-white/8 border border-white/10 text-[9px] font-mono text-slate-400">Enter</kbd>
                                <span>to add symbol and close dialog</span>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ══════════════════════════════════════════════════════════
                TradingView-style "Create New Watchlist" Modal
                ══════════════════════════════════════════════════════════ */}
            <AnimatePresence>
                {showCreateWatchlistModal && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
                        onClick={() => setShowCreateWatchlistModal(false)}
                    >
                        <motion.div
                            initial={{ opacity: 0, y: -16, scale: 0.97 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            exit={{ opacity: 0, y: -16, scale: 0.97 }}
                            className="w-[360px] bg-[#1e222d] border border-[#2a2e39] rounded-2xl shadow-2xl overflow-hidden p-5 flex flex-col gap-4 text-slate-200"
                            onClick={e => e.stopPropagation()}
                        >
                            <div className="flex items-center justify-between border-b border-[#2a2e39] pb-3">
                                <span className="font-bold text-sm font-mono tracking-wider text-white uppercase">
                                    Create New Watchlist
                                </span>
                                <button onClick={() => setShowCreateWatchlistModal(false)} className="text-slate-400 hover:text-white">
                                    <X size={16} />
                                </button>
                            </div>

                            <form onSubmit={handleCreateCustomWatchlist} className="flex flex-col gap-4">
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-xs font-bold text-slate-400 font-mono">Watchlist Name</label>
                                    <input
                                        type="text"
                                        value={newWatchlistNameInput}
                                        onChange={e => setNewWatchlistNameInput(e.target.value)}
                                        placeholder="e.g. Indian IT Stocks, Nifty Options..."
                                        className="w-full bg-[#131722] border border-[#2a2e39] focus:border-[#2962ff] text-white text-xs px-3.5 py-2.5 rounded-xl outline-none font-mono"
                                        autoFocus
                                    />
                                </div>

                                <div className="flex items-center justify-end gap-2 pt-2">
                                    <button
                                        type="button"
                                        onClick={() => setShowCreateWatchlistModal(false)}
                                        className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        disabled={!newWatchlistNameInput.trim()}
                                        className="px-5 py-2 text-xs font-bold text-white bg-[#2962ff] hover:bg-[#1e54e4] rounded-xl disabled:opacity-40 transition-all"
                                    >
                                        Create Watchlist
                                    </button>
                                </div>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

