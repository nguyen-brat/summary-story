import time
import json
import re
import asyncio

class TrackApi:
    def __init__(self, quota_per_minute: int = 15):
        self.quota_per_minute = quota_per_minute
        self.request_timestamps = []
        self.daily_request_count = 0
        self.daily_reset_time = time.time() + 24 * 3600  # Reset every 24h

    def _parse_google_api_error(self, error_message: str):
        """
        Parse Google API error message to extract quota information and retry delay
        Returns: (quota_value, retry_delay_seconds)
        """
        try:
            if error_message.strip().startswith('{'):
                error_json = json.loads(error_message)
                details = error_json.get('error', {}).get('details', [])

                quota_value = None
                retry_delay_seconds = None

                for detail in details:
                    if detail.get('@type') == 'type.googleapis.com/google.rpc.QuotaFailure':
                        violations = detail.get('violations', [])
                        if violations:
                            quota_value = int(violations[0].get('quotaValue', 0))

                    elif detail.get('@type') == 'type.googleapis.com/google.rpc.RetryInfo':
                        retry_delay_str = detail.get('retryDelay', '0s')
                        retry_match = re.search(r'(\d+)s?', retry_delay_str)
                        if retry_match:
                            retry_delay_seconds = int(retry_match.group(1))

                return quota_value, retry_delay_seconds

            quota_match = re.search(r'quotaValue["\s:]*"?(\d+)"?', error_message)
            quota_value = int(quota_match.group(1)) if quota_match else None

            delay_match = re.search(r'retryDelay["\s:]*"?(\d+)s?"?', error_message)
            retry_delay_seconds = int(delay_match.group(1)) if delay_match else None

            return quota_value, retry_delay_seconds

        except Exception as e:
            print(f"Error parsing API error message: {e}")
            return None, None

    async def _rate_limited_llm_call(self, llm_method, *args, **kwargs):
        """
        Wrapper for LLM calls with rate limiting for Google Gemini free tier.
        Dynamically adjusts based on API error responses.
        """
        max_retries = 5
        base_delay = 60 // self.quota_per_minute

        for attempt in range(max_retries):
            try:
                await self._check_rate_limits()

                if asyncio.iscoroutinefunction(llm_method):
                    result = await llm_method(*args, **kwargs)
                else:
                    result = llm_method(*args, **kwargs)

                self._track_request()
                return result

            except Exception as e:
                error_msg = str(e)

                if any(term in error_msg.lower() for term in ['quota', 'rate limit', 'too many requests', '429', 'resource_exhausted']):
                    api_quota_value, api_retry_delay = self._parse_google_api_error(error_msg)

                    if api_quota_value and api_quota_value != self.quota_per_minute:
                        print(f"Updating quota per minute from {self.quota_per_minute} to {api_quota_value}")
                        self.quota_per_minute = api_quota_value

                    if api_retry_delay:
                        wait_time = api_retry_delay
                        print(f"Rate limit exceeded. Using API suggested retry delay: {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
                    else:
                        wait_time = base_delay * (2 ** attempt)
                        print(f"Rate limit exceeded. Using exponential backoff: {wait_time} seconds (attempt {attempt + 1}/{max_retries})")

                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise e

        raise Exception(f"Failed to complete LLM call after {max_retries} attempts")

    async def _check_rate_limits(self):
        """Check and enforce rate limits"""
        current_time = time.time()

        if current_time > self.daily_reset_time:
            self.daily_request_count = 0
            self.daily_reset_time = current_time + 24 * 3600

        if self.daily_request_count >= 1500:
            sleep_time = self.daily_reset_time - current_time
            print(f"Daily request limit (1500) reached. Sleeping for {sleep_time/3600:.2f} hours")
            await asyncio.sleep(sleep_time)
            self.daily_request_count = 0
            self.daily_reset_time = time.time() + 24 * 3600

        self.request_timestamps = [ts for ts in self.request_timestamps if current_time - ts < 60]

        if len(self.request_timestamps) >= self.quota_per_minute:
            oldest_request = min(self.request_timestamps)
            sleep_time = 60 - (current_time - oldest_request)
            if sleep_time > 0:
                print(f"Per-minute limit ({self.quota_per_minute}) reached. Sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)

    def _track_request(self):
        """Track a successful request"""
        current_time = time.time()
        self.request_timestamps.append(current_time)
        self.daily_request_count += 1