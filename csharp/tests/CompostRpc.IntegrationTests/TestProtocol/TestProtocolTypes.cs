
/******************************************************************************/
/*                     G E N E R A T E D   P R O T O C O L                    */
/******************************************************************************/
using System;
using System.Threading.Tasks;
using System.Collections.Generic;
using CompostRpc;

namespace CompostRpc.IntegrationTests;

public enum Status : byte
{
    Ok = 0,
    Warn = 1,
    Err = 2,
    Fail = 255
};

public enum MotorState : sbyte
{
    Off = 0,
    On = 1,
    Start = 2,
    Stop = 3
};

public enum MotorDirection : short
{
    Down = -1000,
    Up = 1000
};

public enum Voltages : int
{
    Mv110_92 = 0,
    Mv98_76 = 1,
    Mv88_07 = 2,
    Mv78_66 = 3,
    Mv70_38 = 4,
    Mv63_08 = 5,
    Mv56_64 = 6,
    Mv50_95 = 7,
    Mv45_92 = 8,
    Mv41_46 = 9,
    Mv37_50 = 10,
    Mv37_50_1 = 11,
    Mv37_50_2 = 12,
    Mv37_50_3 = 13,
    Mv37_50_4 = 14,
    Mv37_50_5 = 15
};

public class BitfieldStruct
{
    [Pack(8)]
    public int Channel { get; set; }
    [Pack(5)]
    public int Inom { get; set; }
    [Pack(4)]
    public int Hsc { get; set; }
    [Pack(9)]
    public int Tnom { get; set; }
    [Pack(4)]
    public Voltages Temp { get; set; }
    [Pack(3)]
    public int Ststart { get; set; }
    [Pack(1)]
    public int Ccm { get; set; }
    [Pack(1)]
    public int Set { get; set; }
    [Pack(1)]
    public int State { get; set; }
    [Pack(1)]
    public int Clear { get; set; }
}

public class ListFirstAttr
{
    public List<short> Data { get; set; } = [];
    public short Min { get; set; }
    public short Max { get; set; }
}

public class ListMidAttr
{
    public short Min { get; set; }
    public List<short> Data { get; set; } = [];
    public short Max { get; set; }
}

public class ListLastAttr
{
    public short Min { get; set; }
    public short Max { get; set; }
    public List<short> Data { get; set; } = [];
}

public class TwoListAttr
{
    public float AvgA { get; set; }
    public List<short> DataA { get; set; } = [];
    public float AvgMerge { get; set; }
    public List<short> DataB { get; set; } = [];
    public float AvgB { get; set; }
}

public class MockDate
{
    public ushort Day { get; set; }
    public byte Month { get; set; }
    public int Year { get; set; }
    public string AsText { get; set; } = string.Empty;
    public List<byte> AsDigits { get; set; } = [];
}

public class MockMotorReport
{
    public MotorState State { get; set; }
    public MotorDirection Direction { get; set; }
    public List<ushort> Voltage { get; set; } = [];
    public List<ushort> Current { get; set; } = [];
}

public class MockMotorControl
{
    public MotorState State { get; set; }
    public MotorDirection Direction { get; set; }
    public ushort PwmDuty { get; set; }
}

public class MockLogMessage
{
    public Status Severity { get; set; }
    public string Message { get; set; } = string.Empty;
    public MockDate Timestamp { get; set; } = new ();
    public byte ByteXor { get; set; }
}

public class MockLfsr
{
    public ulong Polynomial { get; set; }
    public ulong Value { get; set; }
    public MockDate Timestamp { get; set; } = new ();
}
