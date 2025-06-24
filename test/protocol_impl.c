#include <time.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "compost.h"

void assert(int x)
{
    if (!x) {
        fprintf(stderr, "Assertion failed: %s:%d\n", __FILE__,__LINE__);
        exit(1);
    }
}

// Helper functions ******************************************

int16_t slice_min(struct CompostSliceI16 data)
{
    int16_t min = INT16_MAX;
    for (int i = 0; i < data.len; i++) {
        uint16_t elem = compost_slice_get(data, i);
        if (elem < min)
            min = elem;
    }
    return min;
}

int16_t slice_max(struct CompostSliceI16 data)
{
    int16_t max = INT16_MIN;
    for (int i = 0; i < data.len; i++) {
        uint16_t elem = compost_slice_get(data, i);
        if (elem > max)
            max = elem;
    }
    return max;
}

float slice_avg(struct CompostSliceI16 data)
{
    int16_t sum = 0;
    for (int i = 0; i < data.len; i++)
        sum += compost_slice_get(data, i);
    return (float)sum / data.len;
}

#define MOCK_DATE_FMT_LEN 8

void set_mock_date(struct MockDate* dest, time_t epoch)
{
    if (dest->as_digits.ptr == NULL || dest->as_text.ptr == NULL)
        return;
    struct tm *timeinfo = gmtime(&epoch);
    dest->day = timeinfo->tm_mday;
    dest->month = timeinfo->tm_mon + 1; 
    dest->year = timeinfo->tm_year + 1900;
    char tmp[dest->as_text.len+1];
    snprintf(tmp, sizeof(tmp), "%02d%02d%04d", dest->day, dest->month, dest->year);
    compost_str_copy(dest->as_text, tmp);
    for (int i = 0; i < dest->as_text.len; i++)
        dest->as_digits.ptr[i] = dest->as_text.ptr[i] - '0';
}

// ***********************************************************

uint16_t notif_request = 0xFFFF;

void trigger_notification_handler(uint16_t msg_id)
{
    notif_request = msg_id;
}

uint32_t add_int_handler(uint32_t a, uint32_t b)
{
    return a + b;
}

uint32_t sum_list_handler(struct CompostSliceU32 a)
{
    int sum = 0;
    for (int i = 0; i < a.len; i++)
        sum += compost_slice_get(a, i);
    return sum;
}

void void_return_handler(int16_t x)
{
    (void)x;
}

void void_full_handler(void)
{
    return;
}

float divide_float_handler(float a, float b)
{
    return a / b;
}

struct CompostSliceU8 caesar_cipher_handler(struct CompostSliceU8 str, uint8_t offset,
                                          struct CompostAlloc *alloc)
{
    struct CompostSliceU8 ciphertext = compost_slice_u8_new(alloc, str.len);
    for (int i = 0; i < str.len; i++)
        ciphertext.ptr[i] = str.ptr[i] + offset;
    return ciphertext;
}

struct CompostSliceU8 sort_bytes_handler(struct CompostSliceU8 data, struct CompostAlloc *alloc)
{
    struct CompostSliceU8 sorted = compost_slice_u8_new(alloc, data.len);
    // Bubble sort algorithm
    for (int i = data.len - 1; i >= 0; i--) {
        for (int j = 0; j < data.len - 1; j++) {
            if (data.ptr[j] > data.ptr[j + 1]) {
                uint8_t tmp = data.ptr[j];
                data.ptr[j] = data.ptr[j + 1];
                data.ptr[j + 1] = tmp;
            }
        }
        // After each inner cycle, value at index i will
        // be at correct position and can be copied to destination.
        sorted.ptr[i] = data.ptr[i];
    }
    return sorted;
}

struct ListFirstAttr list_first_attr_handler(struct CompostSliceI16 data, struct CompostAlloc *alloc)
{
    struct ListFirstAttr ret = ListFirstAttr_init(alloc, data.len);
    compost_slice_copy(ret.data, data);
    ret.min = slice_min(ret.data);
    ret.max = slice_max(ret.data);
    return ret;
}

struct ListMidAttr list_mid_attr_handler(struct CompostSliceI16 data, struct CompostAlloc *alloc)
{
    struct ListMidAttr ret = ListMidAttr_init(alloc, data.len);
    compost_slice_copy(ret.data, data);
    ret.min = slice_min(ret.data);
    ret.max = slice_max(ret.data);
    return ret;
}

struct ListLastAttr list_last_attr_handler(struct CompostSliceI16 data, struct CompostAlloc *alloc)
{
    struct ListLastAttr ret = ListLastAttr_init(alloc, data.len);
    compost_slice_copy(ret.data, data);
    ret.min = slice_min(ret.data);
    ret.max = slice_max(ret.data);
    return ret;
}

struct TwoListAttr two_list_attr_handler(struct CompostSliceI16 data_a,
                                     struct CompostSliceI16 data_b, struct CompostAlloc *alloc)
{
    struct TwoListAttr ret = TwoListAttr_init(alloc, data_a.len, data_b.len);
    compost_slice_copy(ret.data_a, data_a);
    compost_slice_copy(ret.data_b, data_b);
    ret.avg_a = slice_avg(ret.data_a);
    ret.avg_b = slice_avg(ret.data_b);
    ret.avg_merge = (ret.avg_a + ret.avg_b) / 2.0;
    return ret;
}

struct MockDate epoch_to_date_handler(int32_t epoch, struct CompostAlloc *alloc)
{
    struct MockDate ret = MockDate_init(alloc, MOCK_DATE_FMT_LEN, MOCK_DATE_FMT_LEN);
    set_mock_date(&ret, (time_t)epoch);
    return ret;
}

struct CompostSliceU8 emoji_handler(struct CompostSliceU8 text, struct CompostAlloc *alloc)
{
    static uint8_t tmp[8];
    struct CompostAlloc outside_alloc = compost_alloc_init(tmp, 8);
    if (strncmp((char *)text.ptr, "😘", text.len)) {
        return compost_str_new(&outside_alloc, "🤔"); // Returning slice outside of the TX buffer
    } else {
        return compost_str_new(alloc, "🥰"); // Returning slice inside of the TX buffer
    }
}

struct CompostSliceU32 cat_lists_handler(struct CompostSliceU32 list_a,
                                       struct CompostSliceU32 list_b, struct CompostAlloc *alloc)
{
    struct CompostSliceU32 ret = compost_slice_u32_new(alloc, list_a.len + list_b.len);
    for (int i = 0; i < list_a.len; i++) {
        compost_slice_set(ret, i, compost_slice_get(list_a, i));
    }
    for (int i = 0; i < list_b.len; i++) {
        compost_slice_set(ret, i + list_a.len, compost_slice_get(list_b, i));
    }
    return ret;
}

struct MockLfsr get_random_number_handler(uint64_t seed, uint8_t iter, struct CompostAlloc *alloc)
{
    struct MockLfsr lfsr = MockLfsr_init(alloc, MOCK_DATE_FMT_LEN, MOCK_DATE_FMT_LEN);
    lfsr.polynomial = 0xD800000000000000; //< Copy this value when reimplementing this test
    // LFSR does not work for seed=0 -> store any other value
    lfsr.value = seed == 0 ? 0x1F2E3D4C5B6A7988 : seed;
    for (int i = 0; i < iter; i++)
    {
        uint8_t feedback = lfsr.value & 1;
        // Shift the seed to the right by one bit
        lfsr.value >>= 1;
        // If the feedback bit is 1, apply the polynomial
        if (feedback)
            lfsr.value ^= lfsr.polynomial;
    }
    time_t current_epoch;
    time(&current_epoch);
    set_mock_date(&lfsr.timestamp, current_epoch);
    return lfsr;
}

/* Notification handlers */

uint8_t tx_buf_notif[1024];

void notify_date_handler(struct MockDate date)
{
    (void)date; // Unused
}

void notify_motor_control_handler(struct MockMotorControl control)
{
    assert(control.state == MOTOR_STATE_ON);
    assert(control.direction == MOTOR_DIRECTION_UP);
    assert(control.pwm_duty == 50);

    // Send back a notification as an async response
    struct CompostAlloc alloc = MockMotorReport_alloc_init(tx_buf_notif, sizeof(tx_buf_notif));
    struct MockMotorReport report = MockMotorReport_init(&alloc, 20, 20);
    report.state = MOTOR_STATE_STOP;
    report.direction = MOTOR_DIRECTION_DOWN;
    for (size_t i = 0; i < 20; i++) {
        compost_slice_set(report.voltage, i, i + 11);
        compost_slice_set(report.current, i, i + 41);
    }
    int16_t tx_len = notify_motor_report_store(tx_buf_notif, sizeof(tx_buf_notif), report);
    if (tx_len > 0) {
        fwrite(tx_buf_notif, 1, tx_len, stdout);
        fflush(stdout);
    } else {
        fprintf(stderr, "Failed to serialize motor report\n");
    }
}

void notify_motor_report_handler(struct MockMotorReport report)
{
    assert(report.state == MOTOR_STATE_START);
    assert(report.direction == MOTOR_DIRECTION_UP);
    assert(report.voltage.len == 20);
    assert(report.current.len == 20);
    
    // Send back a notification as an async response
    struct MockMotorControl control = MockMotorControl_init();
    control.state = MOTOR_STATE_STOP;
    control.direction = MOTOR_DIRECTION_DOWN;
    control.pwm_duty = 1200;
    int16_t tx_len = notify_motor_control_store(tx_buf_notif, sizeof(tx_buf_notif), control);
    if (tx_len > 0) {
        fwrite(tx_buf_notif, 1, tx_len, stdout);
        fflush(stdout);
    } else {
        fprintf(stderr, "Failed to serialize motor control\n");
    }
}

void struct_in_param_handler(struct ListFirstAttr structure)
{
    assert(structure.data.len == 10);
    assert(structure.min == 1);
    assert(structure.max == 10);
}

void notify_bitfields_handler(struct BitfieldStruct config)
{
    config.ccm = ~config.ccm;
    config.channel = ~config.channel;
    config.clear = ~config.clear;
    config.hsc = ~config.hsc;
    config.inom = ~config.inom;
    config.set = ~config.set;
    config.state = ~config.state;
    config.ststart = ~config.ststart;
    config.temp = VOLTAGES_MV_37_50;
    config.tnom = ~config.tnom;
    uint16_t tx_len = notify_bitfields_store(tx_buf_notif, sizeof(tx_buf_notif), config);
    fwrite(tx_buf_notif, 1, tx_len, stdout);
    fflush(stdout);
}

void notify_log_handler(struct MockLogMessage log)
{
    (void)log;
}
