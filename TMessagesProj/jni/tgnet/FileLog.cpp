/*
 * This is the source code of tgnet library v. 1.1
 * It is licensed under GNU GPL v. 2 or later.
 * You should have received a copy of the license in this archive (see LICENSE).
 *
 * Copyright Nikolai Kudashov, 2015-2018.
 */

#include <stdio.h>
#include <stdarg.h>
#include <time.h>
#include <sys/time.h>
#include <string>
#include <vector>
#include "FileLog.h"
#include "ConnectionsManager.h"

#ifdef ANDROID
#include <android/log.h>
#endif

#ifndef ANDROID
#define ANDROID_LOG_FATAL 7
#define ANDROID_LOG_ERROR 6
#define ANDROID_LOG_WARN 5
#define ANDROID_LOG_DEBUG 3
#endif

#ifdef DEBUG_VERSION
bool LOGS_ENABLED = true;
#else
bool LOGS_ENABLED = false;
#endif

bool REF_LOGS_ENABLED = false;
bool NETWORK_DEBUG_LOGS_ENABLED = false;

static std::string formatNativeLogMessage(const char *message, va_list args) {
    va_list argsCopy;
    va_copy(argsCopy, args);
    int length = vsnprintf(nullptr, 0, message, argsCopy);
    va_end(argsCopy);
    if (length <= 0) {
        return message != nullptr ? std::string(message) : std::string();
    }
    std::vector<char> buffer((size_t) length + 1);
    va_copy(argsCopy, args);
    vsnprintf(buffer.data(), buffer.size(), message, argsCopy);
    va_end(argsCopy);
    std::string result(buffer.data(), (size_t) length);
    for (char &value : result) {
        if (value == '\n' || value == '\r') {
            value = ' ';
        }
    }
    return result;
}

FileLog &FileLog::getInstance() {
    static FileLog instance;
    return instance;
}

FileLog::FileLog() {
    pthread_mutex_init(&mutex, NULL);
}

void FileLog::init(std::string path) {
    pthread_mutex_lock(&mutex);
    if (path.size() > 0 && logFile == nullptr) {
        logFile = fopen(path.c_str(), "w");
    }
    pthread_mutex_unlock(&mutex);
}

void FileLog::writeNativeLogLine(int androidPriority, const char *fileSeverity, const char *stdoutSeverity, const char *message, va_list args) {
    std::string formattedMessage = formatNativeLogMessage(message, args);
#ifdef ANDROID
    __android_log_print(androidPriority, "tgnet", "%s", formattedMessage.c_str());
#endif

    FileLog &logger = getInstance();
    struct timeval time_now;
    gettimeofday(&time_now, NULL);
    struct tm nowLocal;
    localtime_r(&time_now.tv_sec, &nowLocal);
    char prefix[128];
    snprintf(prefix, sizeof(prefix), "%d-%d %02d:%02d:%02d.%03d %s: ",
             nowLocal.tm_mon + 1,
             nowLocal.tm_mday,
             nowLocal.tm_hour,
             nowLocal.tm_min,
             nowLocal.tm_sec,
             (int) (time_now.tv_usec / 1000),
             fileSeverity);
    std::string line = std::string(prefix) + formattedMessage;

    pthread_mutex_lock(&logger.mutex);
#ifndef ANDROID
    printf("%d-%d %02d:%02d:%02d %s: %s\n",
           nowLocal.tm_mon + 1,
           nowLocal.tm_mday,
           nowLocal.tm_hour,
           nowLocal.tm_min,
           nowLocal.tm_sec,
           stdoutSeverity,
           formattedMessage.c_str());
    fflush(stdout);
#endif
    FILE *logFile = logger.logFile;
    if (logFile) {
        fprintf(logFile, "%s\n", line.c_str());
        fflush(logFile);
    }
    pthread_mutex_unlock(&logger.mutex);
}

void FileLog::fatal(const char *message, ...) {
    if (!LOGS_ENABLED) {
        return;
    }
    va_list argptr;
    va_start(argptr, message);
    writeNativeLogLine(ANDROID_LOG_FATAL, "FATAL ERROR", "FATAL ERROR", message, argptr);
    va_end(argptr);

#ifdef DEBUG_VERSION
    abort();
#endif
}

void FileLog::e(const char *message, ...) {
    if (!LOGS_ENABLED) {
        return;
    }
    va_list argptr;
    va_start(argptr, message);
    writeNativeLogLine(ANDROID_LOG_ERROR, "error", "error", message, argptr);
    va_end(argptr);
}

void FileLog::w(const char *message, ...) {
    if (!LOGS_ENABLED) {
        return;
    }
    va_list argptr;
    va_start(argptr, message);
    writeNativeLogLine(ANDROID_LOG_WARN, "warning", "warning", message, argptr);
    va_end(argptr);
}

void FileLog::d(const char *message, ...) {
    if (!LOGS_ENABLED) {
        return;
    }
    va_list argptr;
    va_start(argptr, message);
    writeNativeLogLine(ANDROID_LOG_DEBUG, "debug", "debug", message, argptr);
    va_end(argptr);
}

static int refsCount = 0;

void FileLog::ref(const char *message, ...) {
    if (!REF_LOGS_ENABLED) {
        return;
    }
    va_list argptr;
    va_start(argptr, message);
    refsCount++;
#ifdef ANDROID
    std::ostringstream s;
    s << refsCount << " refs (+ref): " << message;
    __android_log_vprint(ANDROID_LOG_VERBOSE, "tgnetREF", s.str().c_str(), argptr);
    va_end(argptr);
    va_start(argptr, message);
#endif
    va_end(argptr);
}

void FileLog::delref(const char *message, ...) {
    if (!REF_LOGS_ENABLED) {
        return;
    }
    va_list argptr;
    va_start(argptr, message);
    refsCount--;
#ifdef ANDROID
    std::ostringstream s;
    s << refsCount << " refs (-ref): " << message;
    __android_log_vprint(ANDROID_LOG_VERBOSE, "tgnetREF", s.str().c_str(), argptr);
    va_end(argptr);
    va_start(argptr, message);
#endif
    va_end(argptr);
}
