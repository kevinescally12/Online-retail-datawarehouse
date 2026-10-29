:on error exit
-- GENERADO desde metadatos reales el 2026-10-29. NO ejecutado.
-- Ejecutar con sqlcmd -b o SSMS en modo SQLCMD. Cambiar SOLO la variable de destino.
-- Por seguridad exige una base nueva; nunca reemplaza una existente.
:setvar BaseDestino "OnlineRetail_Origen_Replica"
USE [master];
GO
IF DB_ID(N'$(BaseDestino)') IS NOT NULL THROW 51000, 'La base destino ya existe. Elija un nombre nuevo.', 1;
-- El THROW detiene sqlcmd con -b; en SSMS no continuar después de un error.
GO
CREATE DATABASE [$(BaseDestino)] COLLATE Modern_Spanish_CI_AS;
GO
USE [$(BaseDestino)];
GO
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO
CREATE SCHEMA [staging];
GO
CREATE TABLE [staging].[OperacionesRetail] (
    [IdCarga] bigint IDENTITY(1,1) NOT NULL,
    [HojaOrigen] nvarchar(30) COLLATE Modern_Spanish_CI_AS NOT NULL,
    [NumeroFactura] nvarchar(50) COLLATE Modern_Spanish_CI_AS NULL,
    [CodigoProducto] nvarchar(50) COLLATE Modern_Spanish_CI_AS NULL,
    [Descripcion] nvarchar(500) COLLATE Modern_Spanish_CI_AS NULL,
    [Cantidad] int NULL,
    [FechaFactura] datetime2(7) NULL,
    [PrecioUnitario] decimal(18,4) NULL,
    [IdCliente] nvarchar(50) COLLATE Modern_Spanish_CI_AS NULL,
    [Pais] nvarchar(100) COLLATE Modern_Spanish_CI_AS NULL
);
GO
ALTER TABLE [staging].[OperacionesRetail] ADD CONSTRAINT [PK__Operacio__6C985617C79690AE] PRIMARY KEY CLUSTERED ([IdCarga] ASC);
GO

