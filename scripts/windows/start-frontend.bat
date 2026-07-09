@echo off
title SentinelFlow AI - Frontend Web App
echo ============================================================
echo          SentinelFlow AI - Starting Frontend Server
echo ============================================================
cd /d "%~dp0..\..\frontend"
npm run dev
