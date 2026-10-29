:on error exit
-- GENERADO desde metadatos reales el 2026-10-29. NO ejecutado.
-- Ejecutar con sqlcmd -b o SSMS en modo SQLCMD. Cambiar SOLO la variable de destino.
-- Por seguridad exige una base nueva; nunca reemplaza una existente.
:setvar BaseDestino "OnlineRetail_DW_Replica"
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
CREATE TABLE [dbo].[DimCliente] (
    [ClienteKey] int IDENTITY(1,1) NOT NULL,
    [IdClienteOrigen] nvarchar(50) COLLATE Modern_Spanish_CI_AS NOT NULL,
    [TipoCliente] nvarchar(30) COLLATE Modern_Spanish_CI_AS NOT NULL
);
GO
CREATE TABLE [dbo].[DimFecha] (
    [FechaKey] int NOT NULL,
    [Fecha] date NOT NULL,
    [Dia] tinyint NOT NULL,
    [Mes] tinyint NOT NULL,
    [NombreMes] nvarchar(20) COLLATE Modern_Spanish_CI_AS NOT NULL,
    [Trimestre] tinyint NOT NULL,
    [Anio] smallint NOT NULL
);
GO
CREATE TABLE [dbo].[DimPais] (
    [PaisKey] int IDENTITY(1,1) NOT NULL,
    [NombrePais] nvarchar(100) COLLATE Modern_Spanish_CI_AS NOT NULL
);
GO
CREATE TABLE [dbo].[DimProducto] (
    [ProductoKey] int IDENTITY(1,1) NOT NULL,
    [CodigoProducto] nvarchar(50) COLLATE Modern_Spanish_CI_AS NOT NULL,
    [DescripcionProducto] nvarchar(500) COLLATE Modern_Spanish_CI_AS NOT NULL,
    [CategoriaCodigo] nvarchar(50) COLLATE Modern_Spanish_CI_AS NOT NULL
);
GO
CREATE TABLE [dbo].[DimTipoOperacion] (
    [TipoOperacionKey] int IDENTITY(1,1) NOT NULL,
    [NombreTipo] nvarchar(50) COLLATE Modern_Spanish_CI_AS NOT NULL,
    [Descripcion] nvarchar(250) COLLATE Modern_Spanish_CI_AS NOT NULL
);
GO
CREATE TABLE [dbo].[FactOperacion] (
    [OperacionKey] bigint IDENTITY(1,1) NOT NULL,
    [IdCargaOrigen] bigint NOT NULL,
    [HojaOrigen] nvarchar(30) COLLATE Modern_Spanish_CI_AS NOT NULL,
    [NumeroFactura] nvarchar(50) COLLATE Modern_Spanish_CI_AS NULL,
    [DescripcionOriginal] nvarchar(500) COLLATE Modern_Spanish_CI_AS NULL,
    [FechaKey] int NOT NULL,
    [ProductoKey] int NOT NULL,
    [ClienteKey] int NOT NULL,
    [PaisKey] int NOT NULL,
    [TipoOperacionKey] int NOT NULL,
    [Cantidad] int NULL,
    [PrecioUnitario] decimal(18,4) NULL,
    [Importe] decimal(23,4) NULL
);
GO
ALTER TABLE [dbo].[DimCliente] ADD CONSTRAINT [PK__DimClien__E0D03928670FF4B3] PRIMARY KEY CLUSTERED ([ClienteKey] ASC);
GO
ALTER TABLE [dbo].[DimCliente] ADD CONSTRAINT [UQ__DimClien__B1D57EE0F157800F] UNIQUE NONCLUSTERED ([IdClienteOrigen] ASC);
GO
ALTER TABLE [dbo].[DimFecha] ADD CONSTRAINT [PK__DimFecha__F60A023650BE6836] PRIMARY KEY CLUSTERED ([FechaKey] ASC);
GO
ALTER TABLE [dbo].[DimFecha] ADD CONSTRAINT [UQ__DimFecha__B30C8A5E7DFD5263] UNIQUE NONCLUSTERED ([Fecha] ASC);
GO
ALTER TABLE [dbo].[DimPais] ADD CONSTRAINT [PK__DimPais__680D2C4E4454F1A8] PRIMARY KEY CLUSTERED ([PaisKey] ASC);
GO
ALTER TABLE [dbo].[DimPais] ADD CONSTRAINT [UQ__DimPais__BFA502694ECF7A98] UNIQUE NONCLUSTERED ([NombrePais] ASC);
GO
ALTER TABLE [dbo].[DimProducto] ADD CONSTRAINT [PK__DimProdu__902B83116014DDF2] PRIMARY KEY CLUSTERED ([ProductoKey] ASC);
GO
ALTER TABLE [dbo].[DimProducto] ADD CONSTRAINT [UQ__DimProdu__785B009FEEDF22C8] UNIQUE NONCLUSTERED ([CodigoProducto] ASC);
GO
ALTER TABLE [dbo].[DimTipoOperacion] ADD CONSTRAINT [PK__DimTipoO__64FFE3CFD0B3539C] PRIMARY KEY CLUSTERED ([TipoOperacionKey] ASC);
GO
ALTER TABLE [dbo].[DimTipoOperacion] ADD CONSTRAINT [UQ__DimTipoO__7586661C08FB7FF0] UNIQUE NONCLUSTERED ([NombreTipo] ASC);
GO
ALTER TABLE [dbo].[FactOperacion] ADD CONSTRAINT [PK__FactOper__2E5B3BC894CC8DE8] PRIMARY KEY CLUSTERED ([OperacionKey] ASC);
GO
ALTER TABLE [dbo].[FactOperacion] ADD CONSTRAINT [UQ__FactOper__E5E7A466945D205A] UNIQUE NONCLUSTERED ([IdCargaOrigen] ASC);
GO
ALTER TABLE [dbo].[FactOperacion] WITH CHECK ADD CONSTRAINT [FK_FactOperacion_Cliente] FOREIGN KEY ([ClienteKey]) REFERENCES [dbo].[DimCliente] ([ClienteKey]);
GO
ALTER TABLE [dbo].[FactOperacion] WITH CHECK ADD CONSTRAINT [FK_FactOperacion_Fecha] FOREIGN KEY ([FechaKey]) REFERENCES [dbo].[DimFecha] ([FechaKey]);
GO
ALTER TABLE [dbo].[FactOperacion] WITH CHECK ADD CONSTRAINT [FK_FactOperacion_Pais] FOREIGN KEY ([PaisKey]) REFERENCES [dbo].[DimPais] ([PaisKey]);
GO
ALTER TABLE [dbo].[FactOperacion] WITH CHECK ADD CONSTRAINT [FK_FactOperacion_Producto] FOREIGN KEY ([ProductoKey]) REFERENCES [dbo].[DimProducto] ([ProductoKey]);
GO
ALTER TABLE [dbo].[FactOperacion] WITH CHECK ADD CONSTRAINT [FK_FactOperacion_Tipo] FOREIGN KEY ([TipoOperacionKey]) REFERENCES [dbo].[DimTipoOperacion] ([TipoOperacionKey]);
GO

